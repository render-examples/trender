"""
Trender Main Workflow
Orchestrates the GitHub trending analytics pipeline using Render Workflows.
"""

from render_sdk.workflows import task, start
import asyncio
import asyncpg
import os
import sys
import logging
import traceback
from datetime import datetime, timedelta, date, timezone
from typing import Dict, List

from connections import init_connections, cleanup_connections
from github_api import GitHubAPIClient
from etl.extract import store_raw_repos


# Helper functions
def chunk_list(items: List, size: int) -> List[List]:
    """Split a list into chunks of specified size."""
    return [items[i:i + size] for i in range(0, len(items), size)]


async def init_connections_with_error_handling():
    """
    Initialize connections with consistent error handling.
    
    Returns:
        Tuple of (GitHubAPIClient, asyncpg.Pool)
        
    Raises:
        SystemExit: If connection fails (exits gracefully with status 1)
    """
    try:
        return await init_connections()
    except ConnectionError as e:
        logger.error(f"FATAL: Cannot connect to database: {e}")
        logger.error("Exiting workflow gracefully due to connection failure")
        sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Development mode - set to limit processing for faster iteration
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'
DEV_REPO_LIMIT = int(os.getenv('DEV_REPO_LIMIT', '50'))

# Target languages for analysis
TARGET_LANGUAGES = ['Python', 'TypeScript', 'Go']


@task
async def main_analysis_task() -> Dict:
    """
    Main orchestrator task for the entire analysis workflow.

    Spawns parallel tasks for:
    - 3 language-specific analyses (Python, TypeScript, Go)
    - 1 Render projects fetch

    Returns execution summary.
    """
    execution_start = datetime.now(timezone.utc)
    logger.info(f"Workflow started at {execution_start}")

    try:
        if DEV_MODE:
            # Development mode: Python only + ETL pipeline
            logger.info("DEV_MODE enabled - running Python task only")
            python_result = await fetch_language_repos('Python')
            
            logger.info("Python task completed, starting ETL pipeline")
            
            # Initialize connections for ETL pipeline
            github_api, db_pool = await init_connections_with_error_handling()
            logger.info("Connections initialized for ETL pipeline")
            
            # Run ETL pipeline: Extract from staging → Transform → Load to analytics
            final_result = await aggregate_results([python_result], db_pool, execution_start)
            
            execution_time = (datetime.now(timezone.utc) - execution_start).total_seconds()
            logger.info(f"DEV_MODE workflow completed in {execution_time}s")
            
            # Add dev_mode flag to result
            final_result['dev_mode'] = True
            final_result['languages'] = ['Python']
            
            return final_result
        else:
            # Production mode: Full pipeline
            # Spawn parallel language analysis tasks (they initialize their own connections)
            language_tasks = [
                fetch_language_repos(lang)
                for lang in TARGET_LANGUAGES
            ]
            logger.info(f"Created {len(language_tasks)} language tasks for {TARGET_LANGUAGES}")

            # Execute language analysis and Render projects fetch in parallel
            results = await asyncio.gather(
                *language_tasks,
                fetch_render_repos(),
                return_exceptions=True
            )

            # Log results from parallel tasks
            logger.info(f"Parallel tasks completed. Total results: {len(results)}")
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Task {i} ({TARGET_LANGUAGES[i] if i < len(TARGET_LANGUAGES) else 'render_yaml_search'}) FAILED: {type(result).__name__}: {str(result)}")
                    logger.error("".join(traceback.format_exception(type(result), result, result.__traceback__)))
                else:
                    result_len = len(result) if isinstance(result, (list, dict)) else 'N/A'
                    logger.info(f"Task {i} ({TARGET_LANGUAGES[i] if i < len(TARGET_LANGUAGES) else 'render_yaml_search'}) SUCCESS: {type(result).__name__}, items={result_len}")

            # Aggregate and store final results
            github_api, db_pool = await init_connections_with_error_handling()
            logger.info("Connections initialized for aggregation")
            
            final_result = await aggregate_results(results, db_pool, execution_start)

            return final_result
    finally:
        # Cleanup if connections were initialized
        try:
            await cleanup_connections(github_api, db_pool)
        except Exception:
            pass  # Connections may not have been initialized if error occurred early


@task
async def fetch_language_repos(language: str) -> List[Dict]:
    """
    Fetch and store trending repos for a specific language.

    Args:
        language: Programming language to fetch

    Returns:
        List of enriched repository dictionaries
    """
    logger.info(f"fetch_language_repos START for {language}")
    
    # Initialize connections for this task
    github_api, db_pool = await init_connections_with_error_handling()
    
    try:
        # Search GitHub API (API now filters out repos without language)
        try:
            repos = await github_api.search_repositories(
                language=language,
                sort='stars',
                updated_since=datetime.now(timezone.utc) - timedelta(days=30),
                created_since=datetime.now(timezone.utc) - timedelta(days=180)
            )
            logger.info(f"GitHub API returned {len(repos)} repos for {language} (updated in last 30d, created in last 180d, all with valid language)")
        except Exception as e:
            logger.error(f"search_repositories failed for {language}: {type(e).__name__}: {e}")
            raise

        # Target: 25 repos per language (or DEV_REPO_LIMIT in dev mode)
        target_count = DEV_REPO_LIMIT if DEV_MODE else 25
        
        # Take up to target_count repos
        repos_to_process = repos[:target_count]
        logger.info(f"Processing {len(repos_to_process)} repos for {language} (target={target_count}, DEV_MODE={DEV_MODE})")

        if not repos_to_process:
            logger.warning(f"No repos found for {language}")
            return []

        # Fetch READMEs in parallel (much faster!)
        readme_contents = {}
        readme_tasks = []
        for repo in repos_to_process:
            owner, name = repo.get('full_name', '/').split('/')
            readme_tasks.append(github_api.fetch_readme(owner, name))
        
        readme_results = await asyncio.gather(*readme_tasks, return_exceptions=True)
        for i, repo in enumerate(repos_to_process):
            if not isinstance(readme_results[i], Exception) and readme_results[i]:
                readme_contents[repo.get('full_name')] = readme_results[i]
        
        logger.info(f"Fetched {len(readme_contents)} READMEs for {language}")
        
        # Store raw API responses with READMEs
        await store_raw_repos(repos_to_process, db_pool, source_language=language, readme_contents=readme_contents)

        # Spawn batch analysis task (subtask initializes its own connections)
        # Pass README contents to avoid duplicate API calls
        batch_results = await analyze_repo_batch(repos_to_process, readme_contents)
        
        logger.info(f"fetch_language_repos END for {language}, returning {len(batch_results)} results")
        return batch_results
    finally:
        # Cleanup connections
        await cleanup_connections(github_api, db_pool)


@task
async def analyze_repo_batch(repos: List[Dict], readme_contents: Dict[str, str] = None) -> List[Dict]:
    """
    Analyze a batch of repositories with detailed metrics.
    
    This task runs independently and initializes its own connections.

    Args:
        repos: List of repository dictionaries (JSON-serializable)
        readme_contents: Optional dict mapping repo_full_name to README content (to avoid duplicate API calls)

    Returns:
        List of enriched repository dictionaries
    """
    logger.info(f"analyze_repo_batch START: {len(repos)} repos")
    readme_contents = readme_contents or {}
    
    # Initialize connections for this independent task
    try:
        logger.info("Initializing connections...")
        github_api, db_pool = await init_connections()
        logger.info(f"Connections initialized successfully. Session: {github_api.session is not None}, Pool: {db_pool is not None}")
    except ConnectionError as e:
        logger.error(f"FATAL: Failed to initialize connections: {type(e).__name__}: {str(e)}")
        logger.error(f"Full traceback: {''.join(traceback.format_exception(type(e), e, e.__traceback__))}")
        return []  # Return empty list if we can't even connect
    except Exception as e:
        logger.error(f"FATAL: Failed to initialize connections: {type(e).__name__}: {str(e)}")
        logger.error(f"Full traceback: {''.join(traceback.format_exception(type(e), e, e.__traceback__))}")
        return []  # Return empty list if we can't even connect
    
    try:
        enriched_repos = []

        # Process repos in batches of 10
        for batch_idx, batch in enumerate(chunk_list(repos, size=10)):
            batch_tasks = [
                analyze_single_repo(repo, github_api, db_pool, readme_contents.get(repo.get('full_name')))
                for repo in batch
            ]

            # Gather with exceptions to continue on failures
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Filter out exceptions and collect successful results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    repo_name = batch[i].get('full_name', 'unknown')
                    logger.error(f"Failed to analyze {repo_name}: {type(result).__name__}: {str(result)}")
                    logger.error(f"Full traceback: {''.join(traceback.format_exception(type(result), result, result.__traceback__))}")
                elif result is not None:
                    enriched_repos.append(result)

        logger.info(f"analyze_repo_batch END: {len(enriched_repos)} enriched")
        return enriched_repos
    finally:
        # Cleanup connections
        await cleanup_connections(github_api, db_pool)


async def analyze_single_repo(repo: Dict, github_api: GitHubAPIClient,
                              db_pool: asyncpg.Pool, readme_content: str = None) -> Dict:
    """
    Analyze a single repository with detailed metrics.

    Args:
        repo: Repository dictionary
        github_api: GitHub API client
        db_pool: Database connection pool
        readme_content: Optional pre-fetched README content (to avoid duplicate API call)

    Returns:
        Enriched repository dictionary
    """
    # Validate repo_full_name exists and is well-formed
    repo_full_name = repo.get('full_name')
    if not (repo_full_name and '/' in repo_full_name):
        logger.warning(f"Skipping repo with invalid full_name: {repo_full_name}")
        return None
    
    # Validate all required fields are present
    required_fields = {
        'language': repo.get('language'),
        'created_at': repo.get('created_at'),
        'updated_at': repo.get('updated_at')
    }
    
    for field_name, field_value in required_fields.items():
        if not field_value:
            logger.warning(f"Skipping repo {repo_full_name} - missing {field_name}")
            return None
    
    # Extract validated values
    owner, name = repo_full_name.split('/', 1)
    language = required_fields['language']
    
    # Fetch README if not provided
    if readme_content is None:
        try:
            readme = await github_api.fetch_readme(owner, name)
        except Exception as e:
            logger.debug(f"Failed to fetch README for {repo_full_name}: {e}")
            readme = None
    else:
        readme = readme_content

    # Build enriched repo data
    enriched = {
        'repo_full_name': repo.get('full_name'),
        'repo_url': repo.get('html_url'),
        'language': language,
        'description': repo.get('description'),
        'readme_content': readme,
        'stars': repo.get('stargazers_count', 0),
        'created_at': repo.get('created_at'),
        'updated_at': repo.get('updated_at'),
    }
    
    # Parse ISO datetime strings to timezone-aware datetime objects for PostgreSQL
    # GitHub API returns ISO 8601 with 'Z' suffix (UTC timezone)
    # Keep timezone-aware for TIMESTAMPTZ columns
    if isinstance(enriched['created_at'], str):
        enriched['created_at'] = datetime.fromisoformat(enriched['created_at'].replace('Z', '+00:00'))
    if isinstance(enriched['updated_at'], str):
        enriched['updated_at'] = datetime.fromisoformat(enriched['updated_at'].replace('Z', '+00:00'))

    # Store in staging layer
    logger.info(f"Storing {enriched['repo_full_name']} to staging (language={language})")
    await store_in_staging(enriched, db_pool)
    
    logger.info(f"Successfully stored {enriched['repo_full_name']} to staging")

    # Return minimal summary (data is already in DB, no need to pass full objects)
    return {
        'repo_full_name': enriched['repo_full_name'],
        'language': enriched['language'],
        'stars': enriched['stars']
    }


async def store_in_staging(repo: Dict, db_pool: asyncpg.Pool):
    """Store enriched repository data in staging layer."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO stg_repos_validated
                (repo_full_name, repo_url, language, description, stars,
                 created_at, updated_at, readme_content)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (repo_full_name) DO UPDATE SET
                stars = EXCLUDED.stars,
                updated_at = EXCLUDED.updated_at,
                readme_content = EXCLUDED.readme_content,
                loaded_at = NOW()
        """, repo.get('repo_full_name'), repo.get('repo_url'), repo.get('language'),
            repo.get('description'), repo.get('stars', 0),
            repo.get('created_at'), repo.get('updated_at'),
            repo.get('readme_content'))


@task
async def fetch_render_repos() -> List[Dict]:
    """
    Fetch independent Render projects using code search.
    Searches for repositories with render.yaml in root directory.
    All repos are assigned language='render' (lowercase) for identification.
    
    Returns:
        List of repository dictionaries
    """
    logger.info("fetch_render_repos START - code search for render.yaml")
    
    # Initialize connections
    github_api, db_pool = await init_connections_with_error_handling()
    
    try:
        # Code search for render.yaml in root directory
        # API assigns language='render' (lowercase) to all repos automatically
        # Request 100 initially to ensure we get 25+ repos
        # Filter for repos created within last 18 months
        eighteen_months_ago = datetime.now(timezone.utc) - timedelta(days=548)  # 18 months ≈ 548 days
        repos = await github_api.search_render_projects(limit=100, created_since=eighteen_months_ago)
        logger.info(f"Found {len(repos)} repos with render.yaml in root (all with language='render')")
        
        if not repos:
            logger.warning("No Render projects found via code search")
            return []
        
        # Target: 25 render projects
        target_count = 25
        repos_to_process = repos[:target_count]
        logger.info(f"Processing {len(repos_to_process)} render projects (target={target_count})")
        
        # Fetch READMEs in parallel (same as language repos)
        readme_contents = {}
        readme_tasks = []
        for repo in repos_to_process:
            owner, name = repo.get('full_name', '/').split('/')
            readme_tasks.append(github_api.fetch_readme(owner, name))
        
        readme_results = await asyncio.gather(*readme_tasks, return_exceptions=True)
        for i, repo in enumerate(repos_to_process):
            if not isinstance(readme_results[i], Exception) and readme_results[i]:
                readme_contents[repo.get('full_name')] = readme_results[i]
        
        logger.info(f"Fetched {len(readme_contents)} READMEs for render repos")
        
        # Store in raw layer with READMEs
        await store_raw_repos(repos_to_process, db_pool, source_language='render', readme_contents=readme_contents)
        
        # Analyze batch (stores in staging) with README contents
        analyzed = await analyze_repo_batch(repos_to_process, readme_contents)
        
        logger.info(f"fetch_render_repos END: {len(analyzed)} analyzed")
        return analyzed
        
    finally:
        await cleanup_connections(github_api, db_pool)


async def aggregate_results(all_results: List, db_pool: asyncpg.Pool,
                            execution_start: datetime) -> Dict:
    """
    Simplified ETL: Extract from staging, order by stars, load to analytics.
    
    Args:
        all_results: List of results from parallel tasks
        db_pool: Database connection pool
        execution_start: Workflow execution start time
    
    Returns:
        Execution summary dictionary
    """
    logger.info("aggregate_results START")
    
    # Count successful task results
    successful_tasks = sum(1 for r in all_results if not isinstance(r, Exception) and isinstance(r, list) and len(r) > 0)
    logger.info(f"Successful tasks: {successful_tasks}/{len(all_results)}")
    
    async with db_pool.acquire() as conn:
        # Extract repos in two parts:
        # 1. Top trending repos per language (balanced across Python, TypeScript, Go)
        # 2. ALL qualifying Render repos (language='render')
        
        # Part 1: Top 50 repos per language for balanced representation
        general_repos = await conn.fetch("""
            WITH ranked_repos AS (
                SELECT
                    srv.repo_full_name,
                    srv.repo_url,
                    srv.language,
                    srv.description,
                    srv.stars,
                    srv.created_at,
                    srv.updated_at,
                    srv.readme_content,
                    sre.render_category,
                    sre.render_services,
                    sre.render_complexity_score,
                    sre.has_blueprint_button,
                    sre.service_count,
                    ROW_NUMBER() OVER (PARTITION BY srv.language ORDER BY srv.stars DESC) as lang_rank
                FROM stg_repos_validated srv
                LEFT JOIN stg_render_enrichment sre ON srv.repo_full_name = sre.repo_full_name
            )
            SELECT
                repo_full_name,
                repo_url,
                language,
                description,
                stars,
                created_at,
                updated_at,
                readme_content,
                render_category,
                render_services,
                render_complexity_score,
                has_blueprint_button,
                service_count
            FROM ranked_repos
            WHERE lang_rank <= 50
            ORDER BY stars DESC
        """)
        
        # Part 2: ALL Render repos (identified by language='render')
        render_repos = await conn.fetch("""
            SELECT
                srv.repo_full_name,
                srv.repo_url,
                srv.language,
                srv.description,
                srv.stars,
                srv.created_at,
                srv.updated_at,
                srv.readme_content,
                sre.render_category,
                sre.render_services,
                sre.render_complexity_score,
                sre.has_blueprint_button,
                sre.service_count
            FROM stg_repos_validated srv
            LEFT JOIN stg_render_enrichment sre ON srv.repo_full_name = sre.repo_full_name
            WHERE srv.language = 'render'
            ORDER BY srv.stars DESC
        """)
        
        # Merge repos (deduplicate by repo_full_name)
        seen_repos = set()
        repos = []
        
        for repo in list(general_repos) + list(render_repos):
            repo_name = repo.get('repo_full_name')
            if repo_name not in seen_repos:
                seen_repos.add(repo_name)
                repos.append(repo)
        
        logger.info(f"Extracted {len(general_repos)} general + {len(render_repos)} render repos = {len(repos)} total (deduplicated) from staging")
        
        if not repos:
            logger.warning("No repos found in staging for analytics")
            return {
                'repos_processed': 0,
                'execution_time': (datetime.now(timezone.utc) - execution_start).total_seconds(),
                'success': True
            }
        
        # Load to analytics (consolidated logic)
        await load_to_analytics_simple(repos, conn)
        
        return {
            'repos_processed': len(repos),
            'execution_time': (datetime.now(timezone.utc) - execution_start).total_seconds(),
            'success': True
        }


def calculate_recency_score(created_at, now: datetime) -> float:
    """
    Calculate recency score based on repo age with exponential decay.
    Heavily favors newer repos to prioritize emerging projects.
    
    Args:
        created_at: Repository creation datetime (string or datetime object)
        now: Current datetime for calculating age
        
    Returns:
        Recency score between 0.01 and 1.0
    """
    if not created_at:
        return 0.0
    
    # Ensure created_at is timezone-aware
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    elif created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    
    age_days = (now - created_at).days
    
    # Exponential decay: heavily favor very recent repos
    if age_days <= 14:
        return 1.0
    elif age_days <= 30:
        return 0.85
    elif age_days <= 60:
        return 0.60
    elif age_days <= 90:
        return 0.35
    elif age_days <= 180:
        return 0.15
    elif age_days <= 365:
        return 0.05
    else:
        return 0.01  # Minimal score for older repos


async def load_to_analytics_simple(repos: List, conn: asyncpg.Connection):
    """
    Simplified load: upsert dimensions and facts with recency-weighted scoring.
    
    Scoring formula (heavily favors recent repos):
    - 70% recency score (exponential decay based on repo creation date)
    - 30% normalized star count
    
    This prioritizes emerging/trending projects over established popular repos.
    
    Args:
        repos: List of repository records from staging
        conn: Database connection
    """
    today = date.today()
    now = datetime.now(timezone.utc)
    
    # Calculate max stars for normalization (separately for general and Render repos)
    general_repos = [r for r in repos if r.get('language') != 'render']
    render_repos = [r for r in repos if r.get('language') == 'render']
    
    max_stars_general = max([r.get('stars', 1) for r in general_repos]) if general_repos else 1
    max_stars_render = max([r.get('stars', 1) for r in render_repos]) if render_repos else 1
    
    logger.info(f"Max stars - General: {max_stars_general}, Render: {max_stars_render}")
    
    for idx, repo in enumerate(repos, 1):
        repo_name = repo['repo_full_name']
        if not repo_name:
            continue
        
        try:
            # Upsert into dim_repositories (simplified, no SCD Type 2)
            await conn.execute("""
                INSERT INTO dim_repositories
                    (repo_full_name, repo_url, description, readme_content, language, 
                     created_at, render_category, valid_from, is_current)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), TRUE)
                ON CONFLICT (repo_full_name) 
                WHERE is_current = TRUE
                DO UPDATE SET
                    repo_url = EXCLUDED.repo_url,
                    description = EXCLUDED.description,
                    readme_content = EXCLUDED.readme_content
            """, repo_name, repo['repo_url'], repo['description'],
                repo['readme_content'], repo['language'], repo['created_at'],
                'community')
            
            # Get keys for fact table
            repo_key = await conn.fetchval("""
                SELECT repo_key FROM dim_repositories
                WHERE repo_full_name = $1 AND is_current = TRUE
            """, repo_name)
            
            if not repo_key:
                logger.warning(f"Missing repo_key for {repo_name}, skipping")
                continue
            
            # Get language_key (all 4 languages should exist: Python, TypeScript, Go, render)
            language_key = await conn.fetchval("""
                SELECT language_key FROM dim_languages
                WHERE language_name = $1
            """, repo['language'])
            
            if not language_key:
                logger.error(f"Language '{repo['language']}' not found in dim_languages for {repo_name}. Expected one of: Python, TypeScript, Go, render")
                continue
            
            # Calculate momentum score using star-recency formula
            stars = repo.get('stars', 0)
            is_render = repo.get('language') == 'render'
            
            # Normalize stars based on appropriate max (general vs render)
            max_stars = max_stars_render if is_render else max_stars_general
            normalized_stars = stars / max_stars if max_stars > 0 else 0.0
            
            # Calculate recency score
            recency_score = calculate_recency_score(repo.get('created_at'), now)
            
            # Final momentum score: 70% recency + 30% stars
            # This heavily favors newer repos to surface emerging projects
            momentum_score = (recency_score * 0.7) + (normalized_stars * 0.3)
            
            logger.info(f"Score for {repo_name}: stars={stars}, norm_stars={normalized_stars:.3f}, recency={recency_score:.2f}, momentum={momentum_score:.3f}")
            
            # Insert fact snapshot with calculated momentum score
            await conn.execute("""
                INSERT INTO fact_repo_snapshots
                    (repo_key, language_key, snapshot_date, stars,
                     star_velocity, activity_score, momentum_score,
                     rank_overall, rank_in_language)
                VALUES ($1, $2, $3, $4, 0, 0, $5, $6, NULL)
                ON CONFLICT (repo_key, snapshot_date) DO UPDATE SET
                    stars = EXCLUDED.stars,
                    momentum_score = EXCLUDED.momentum_score,
                    rank_overall = EXCLUDED.rank_overall
            """, repo_key, language_key, today, repo['stars'], momentum_score, idx)
            
            # If Render repo, also populate fact_render_usage
            if is_render and repo.get('render_services'):
                render_services = repo.get('render_services', [])
                complexity = repo.get('render_complexity_score', 0)
                has_blueprint = repo.get('has_blueprint_button', False)
                
                for service_type in render_services:
                    # Get service_key from dim_render_services
                    service_key = await conn.fetchval("""
                        SELECT service_key FROM dim_render_services
                        WHERE service_type = $1
                    """, service_type)
                    
                    if service_key:
                        await conn.execute("""
                            INSERT INTO fact_render_usage
                                (repo_key, service_key, snapshot_date, service_count,
                                 complexity_score, has_blueprint)
                            VALUES ($1, $2, $3, 1, $4, $5)
                            ON CONFLICT (repo_key, service_key, snapshot_date) DO UPDATE SET
                                complexity_score = EXCLUDED.complexity_score,
                                has_blueprint = EXCLUDED.has_blueprint
                        """, repo_key, service_key, today, complexity, has_blueprint)
                        
                        logger.debug(f"Inserted fact_render_usage for {repo_name}, service: {service_type}")
            
        except Exception as e:
            logger.error(f"Error loading repo {repo_name}: {type(e).__name__}: {e}")
            continue
    
    logger.info(f"Loaded {len(repos)} repos to analytics layer")


if __name__ == "__main__":
    # Start the Render Workflows task server
    # This registers all @task decorated functions and begins listening for task execution requests
    start()
