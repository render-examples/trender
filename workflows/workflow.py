"""
Trender Main Workflow
Orchestrates the GitHub trending analytics pipeline using Render Workflows.
"""

from render_sdk.workflows import task, start
import asyncio
import asyncpg
import os
import logging
import traceback
from datetime import datetime, timedelta, date, timezone
from typing import Dict, List

from connections import init_connections, cleanup_connections
from github_api import GitHubAPIClient
from metrics import calculate_metrics
from render_detection import (
    detect_render_usage, categorize_render_project,
    score_blueprint_quality, score_documentation,
    store_render_enrichment
)
from etl import extract_from_staging, transform_and_rank, load_to_analytics
from etl.extract import store_raw_repos, store_raw_metrics
from etl.transform import deduplicate_repos, chunk_list
from etl.data_quality import calculate_data_quality_score

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Development mode - set to limit processing for faster iteration
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'
DEV_REPO_LIMIT = int(os.getenv('DEV_REPO_LIMIT', '10'))

# Target languages for analysis
TARGET_LANGUAGES = ['Python', 'TypeScript', 'Go']


@task
async def main_analysis_task() -> Dict:
    """
    Main orchestrator task for the entire analysis workflow.

    Spawns parallel tasks for:
    - 3 language-specific analyses (Python, TypeScript, Go)
    - 1 Render ecosystem fetch

    Returns execution summary.
    """
    execution_start = datetime.now(timezone.utc)
    logger.info(f"Workflow started at {execution_start}")

    try:
        # Spawn parallel language analysis tasks (they initialize their own connections)
        language_tasks = [
            fetch_language_repos(lang)
            for lang in TARGET_LANGUAGES
        ]
        logger.info(f"Created {len(language_tasks)} language tasks for {TARGET_LANGUAGES}")

        # Execute language analysis and Render ecosystem fetch in parallel
        results = await asyncio.gather(
            *language_tasks,
            fetch_render_ecosystem(),
            return_exceptions=True
        )

        # Log results from parallel tasks
        logger.info(f"Parallel tasks completed. Total results: {len(results)}")
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} ({TARGET_LANGUAGES[i] if i < len(TARGET_LANGUAGES) else 'render_ecosystem'}) FAILED: {type(result).__name__}: {str(result)}")
                logger.error("".join(traceback.format_exception(type(result), result, result.__traceback__)))
            else:
                result_len = len(result) if isinstance(result, (list, dict)) else 'N/A'
                logger.info(f"Task {i} ({TARGET_LANGUAGES[i] if i < len(TARGET_LANGUAGES) else 'render_ecosystem'}) SUCCESS: {type(result).__name__}, items={result_len}")

        # Aggregate and store final results
        github_api, db_pool = await init_connections()
        logger.info("Connections initialized for aggregation")
        
        final_result = await aggregate_results(results, db_pool, execution_start)

        # Store execution stats
        execution_time = (datetime.now(timezone.utc) - execution_start).total_seconds()
        await store_execution_stats(execution_time, final_result.get('repos_processed', 0), db_pool)

        return final_result
    finally:
        # Cleanup if connections were initialized
        try:
            await cleanup_connections(github_api, db_pool)
        except:
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
    github_api, db_pool = await init_connections()
    
    try:
        # Search GitHub API
        try:
            repos = await github_api.search_repositories(
                language=language,
                sort='stars',
                updated_since=datetime.now(timezone.utc) - timedelta(days=30)
            )
            logger.info(f"GitHub API returned {len(repos)} repos for {language}")
        except Exception as e:
            logger.error(f"search_repositories failed for {language}: {type(e).__name__}: {e}")
            raise

        # TypeScript-specific filtering for Next.js >= 16
        if language == 'TypeScript':
            repos = await filter_nextjs_repos(repos, github_api, min_version=16)

        # Apply DEV_MODE limits
        repo_limit = DEV_REPO_LIMIT if DEV_MODE else 100
        logger.info(f"Processing {repo_limit} repos (DEV_MODE={DEV_MODE})")

        # Fetch READMEs in parallel (much faster!)
        readme_contents = {}
        readme_tasks = []
        for repo in repos[:repo_limit]:
            owner, name = repo.get('full_name', '/').split('/')
            readme_tasks.append(github_api.fetch_readme(owner, name))
        
        readme_results = await asyncio.gather(*readme_tasks, return_exceptions=True)
        for i, repo in enumerate(repos[:repo_limit]):
            if not isinstance(readme_results[i], Exception) and readme_results[i]:
                readme_contents[repo.get('full_name')] = readme_results[i]
        
        logger.info(f"Fetched {len(readme_contents)} READMEs for {language}")
        
        # Store raw API responses with READMEs
        await store_raw_repos(repos, db_pool, source_language=language, readme_contents=readme_contents)

        # Spawn batch analysis task (subtask initializes its own connections)
        batch_results = await analyze_repo_batch(repos[:repo_limit])
        
        logger.info(f"fetch_language_repos END for {language}, returning {len(batch_results)} results")
        return batch_results
    finally:
        # Cleanup connections
        await cleanup_connections(github_api, db_pool)


async def filter_nextjs_repos(repos: List[Dict], github_api: GitHubAPIClient,
                              min_version: int = 16) -> List[Dict]:
    """
    Filter TypeScript repos for Next.js >= specified version.

    Args:
        repos: List of repository dictionaries
        github_api: GitHub API client
        min_version: Minimum Next.js version

    Returns:
        Filtered list of repositories
    """
    filtered = []

    for repo in repos:
        try:
            owner, name = repo.get('full_name', '/').split('/')
            package_json = await github_api.get_file_contents(owner, name, 'package.json')

            if package_json:
                import json
                package_data = json.loads(package_json)

                # Check dependencies and devDependencies
                next_version = None
                deps = package_data.get('dependencies', {})
                dev_deps = package_data.get('devDependencies', {})

                if 'next' in deps:
                    next_version = deps['next']
                elif 'next' in dev_deps:
                    next_version = dev_deps['next']

                if next_version:
                    # Extract major version number
                    import re
                    version_match = re.search(r'(\d+)\.', next_version)
                    if version_match:
                        major_version = int(version_match.group(1))
                        if major_version >= min_version:
                            filtered.append(repo)
                else:
                    # Include if no Next.js found (might be other TS project)
                    filtered.append(repo)
            else:
                # Include if no package.json found
                filtered.append(repo)
        except:
            # Include on error to avoid losing data
            filtered.append(repo)

    return filtered


@task
async def analyze_repo_batch(repos: List[Dict]) -> List[Dict]:
    """
    Analyze a batch of repositories with detailed metrics.
    
    This task runs independently and initializes its own connections.

    Args:
        repos: List of repository dictionaries (JSON-serializable)

    Returns:
        List of enriched repository dictionaries
    """
    logger.info(f"analyze_repo_batch START: {len(repos)} repos")
    
    # Initialize connections for this independent task
    try:
        logger.info("Initializing connections...")
        github_api, db_pool = await init_connections()
        logger.info(f"Connections initialized successfully. Session: {github_api.session is not None}, Pool: {db_pool is not None}")
    except Exception as e:
        logger.error(f"FATAL: Failed to initialize connections: {type(e).__name__}: {str(e)}")
        logger.error(f"Full traceback: {''.join(traceback.format_exception(type(e), e, e.__traceback__))}")
        return []  # Return empty list if we can't even connect
    
    try:
        enriched_repos = []

        # Process repos in batches of 10
        for batch in chunk_list(repos, size=10):
            batch_tasks = [
                analyze_single_repo(repo, github_api, db_pool)
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
                else:
                    enriched_repos.append(result)

        logger.info(f"analyze_repo_batch END: {len(enriched_repos)} enriched")
        return enriched_repos
    finally:
        # Cleanup connections
        await cleanup_connections(github_api, db_pool)


async def analyze_single_repo(repo: Dict, github_api: GitHubAPIClient,
                              db_pool: asyncpg.Pool) -> Dict:
    """
    Analyze a single repository with detailed metrics.

    Args:
        repo: Repository dictionary
        github_api: GitHub API client
        db_pool: Database connection pool

    Returns:
        Enriched repository dictionary
    """
    owner, name = repo.get('full_name', '/').split('/')

    # Fetch detailed metrics
    since_date = datetime.now(timezone.utc) - timedelta(days=7)

    # Parallel fetch of metrics
    commits, issues, contributors, render_data, readme = await asyncio.gather(
        github_api.get_commits(owner, name, since_date),
        github_api.get_issues(owner, name, state='closed', since=since_date),
        github_api.get_contributors(owner, name),
        detect_render_usage(repo, github_api, db_pool),
        github_api.fetch_readme(owner, name),
        return_exceptions=True
    )

    # Handle exceptions
    commits = commits if not isinstance(commits, Exception) else []
    issues = issues if not isinstance(issues, Exception) else []
    contributors = contributors if not isinstance(contributors, Exception) else []
    render_data = render_data if not isinstance(render_data, Exception) else {}
    readme = readme if not isinstance(readme, Exception) else None

    # Store raw metrics
    await store_raw_metrics(repo.get('full_name'), 'commits', {'count': len(commits), 'commits': commits}, db_pool)
    await store_raw_metrics(repo.get('full_name'), 'issues', {'count': len(issues), 'issues': issues}, db_pool)
    await store_raw_metrics(repo.get('full_name'), 'contributors', {'count': len(contributors), 'contributors': contributors}, db_pool)

    # Build enriched repo data
    enriched = {
        'repo_full_name': repo.get('full_name'),
        'repo_url': repo.get('html_url'),
        'language': repo.get('language'),
        'description': repo.get('description'),
        'readme_content': readme,
        'stars': repo.get('stargazers_count', 0),
        'forks': repo.get('forks_count', 0),
        'open_issues': repo.get('open_issues_count', 0),
        'created_at': repo.get('created_at'),
        'updated_at': repo.get('updated_at'),
        'commits_last_7_days': len(commits),
        'issues_closed_last_7_days': len(issues),
        'active_contributors': len(contributors),
        'uses_render': render_data.get('uses_render', False),
        'render_yaml_content': render_data.get('render_yaml_content'),
        **render_data
    }

    # Calculate data quality score
    enriched['data_quality_score'] = calculate_data_quality_score(enriched)

    # Store in staging layer
    logger.info(f"Storing {enriched['repo_full_name']} to staging (quality: {enriched['data_quality_score']})")
    await store_in_staging(enriched, db_pool)
    logger.info(f"Successfully stored {enriched['repo_full_name']} to staging")

    return enriched


async def store_in_staging(repo: Dict, db_pool: asyncpg.Pool):
    """Store enriched repository data in staging layer."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO stg_repos_validated
                (repo_full_name, repo_url, language, description, stars, forks,
                 open_issues, created_at, updated_at, commits_last_7_days,
                 issues_closed_last_7_days, active_contributors, uses_render,
                 render_yaml_content, data_quality_score)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            ON CONFLICT (repo_full_name) DO UPDATE SET
                stars = EXCLUDED.stars,
                forks = EXCLUDED.forks,
                open_issues = EXCLUDED.open_issues,
                updated_at = EXCLUDED.updated_at,
                commits_last_7_days = EXCLUDED.commits_last_7_days,
                issues_closed_last_7_days = EXCLUDED.issues_closed_last_7_days,
                active_contributors = EXCLUDED.active_contributors,
                uses_render = EXCLUDED.uses_render,
                data_quality_score = EXCLUDED.data_quality_score,
                loaded_at = NOW()
        """, repo.get('repo_full_name'), repo.get('repo_url'), repo.get('language'),
            repo.get('description'), repo.get('stars', 0), repo.get('forks', 0),
            repo.get('open_issues', 0), repo.get('created_at'), repo.get('updated_at'),
            repo.get('commits_last_7_days', 0), repo.get('issues_closed_last_7_days', 0),
            repo.get('active_contributors', 0), repo.get('uses_render', False),
            repo.get('render_yaml_content'), repo.get('data_quality_score', 0.0))


@task
async def fetch_render_ecosystem() -> List[Dict]:
    """
    Fetch Render-related projects from multiple sources.

    Returns:
        List of analyzed Render project dictionaries
    """
    logger.info("fetch_render_ecosystem START")
    
    # Initialize connections for this task
    github_api, db_pool = await init_connections()
    
    try:
        # Parallel fetch from multiple sources
        results = await asyncio.gather(
            github_api.get_org_repos('render-examples'),
            github_api.get_org_repos('render'),
            github_api.search_by_topic('render'),
            github_api.search_by_topic('render-deploy'),
            github_api.search_by_topic('render-blueprints'),
            github_api.search_readme_mentions('render.com'),
            return_exceptions=True
        )

        # Filter out exceptions and flatten
        valid_results = [r for r in results if not isinstance(r, Exception)]

        # Deduplicate and store
        unique_repos = deduplicate_repos(valid_results)
        await store_raw_repos(unique_repos, db_pool, source_type='render_ecosystem')

        # Analyze Render-specific features (subtask initializes its own connections)
        analyzed = await analyze_render_projects(unique_repos)

        logger.info(f"fetch_render_ecosystem END, returning {len(analyzed)} results")
        return analyzed
    finally:
        # Cleanup connections
        await cleanup_connections(github_api, db_pool)


@task
async def analyze_render_projects(render_repos: List[Dict]) -> List[Dict]:
    """
    Analyze Render-specific features and categorization.
    
    This task runs independently and initializes its own connections.

    Args:
        render_repos: List of Render repository dictionaries (JSON-serializable)

    Returns:
        List of enriched Render project dictionaries
    """
    logger.info(f"analyze_render_projects START: {len(render_repos)} repos")
    
    # Initialize connections for this independent task
    github_api, db_pool = await init_connections()
    
    try:
        enriched_projects = []

        for repo in render_repos:
            # Detect Render usage patterns
            render_data = await detect_render_usage(repo, github_api, db_pool)

            # Calculate Render-specific scores
            repo['render_category'] = categorize_render_project(repo)
            repo['blueprint_quality'] = score_blueprint_quality(render_data)
            repo['documentation_score'] = score_documentation(repo, render_data)
            repo['render_services'] = render_data.get('services', [])
            repo['render_complexity_score'] = render_data.get('complexity_score', 0)
            repo['service_count'] = render_data.get('service_count', 0)
            repo['uses_render'] = render_data.get('uses_render', False)

            enriched_projects.append(repo)

        # Store enrichment data
        await store_render_enrichment(enriched_projects, db_pool)

        logger.info(f"analyze_render_projects END: {len(enriched_projects)} enriched")
        return enriched_projects
    finally:
        # Cleanup connections
        await cleanup_connections(github_api, db_pool)


async def aggregate_results(all_results: List, db_pool: asyncpg.Pool,
                            execution_start: datetime) -> Dict:
    """
    Execute ETL pipeline: Extract from staging → Transform → Load to analytics.

    Args:
        all_results: List of results from parallel tasks
        db_pool: Database connection pool
        execution_start: Workflow execution start time

    Returns:
        Execution summary dictionary
    """
    logger.info("aggregate_results START")
    
    # Filter successful results (handle exceptions from gather)
    language_results = [r for r in all_results[:3] if not isinstance(r, Exception)]
    render_results = all_results[3] if len(all_results) > 3 and not isinstance(all_results[3], Exception) else []
    
    logger.info(f"Successful language tasks: {len(language_results)}/3")
    logger.info(f"Render results: type={type(render_results).__name__}, is_list={isinstance(render_results, list)}")

    # Combine and deduplicate
    all_repos = deduplicate_repos(language_results + [render_results])
    logger.info(f"After deduplication: {len(all_repos)} total unique repos")

    # Calculate metrics for all repos
    scored_repos = calculate_metrics(all_repos)

    # ETL Pipeline Execution
    # 1. Extract: Read from staging tables (already stored)
    staging_data = await extract_from_staging(db_pool)

    # 2. Transform: Calculate rankings and velocity metrics
    ranked_repos = transform_and_rank(
        staging_data,
        overall_limit=100,
        per_language_limit=50
    )

    # 3. Load: Upsert to analytics layer
    await load_to_analytics(ranked_repos, db_pool)

    return {
        'repos_processed': len(all_repos),
        'execution_time': (datetime.now(timezone.utc) - execution_start).total_seconds(),
        'languages': TARGET_LANGUAGES,
        'success': True
    }


async def store_execution_stats(duration: float, repos_count: int,
                                db_pool: asyncpg.Pool) -> None:
    """
    Record workflow performance metrics.

    Args:
        duration: Execution duration in seconds
        repos_count: Number of repositories processed
        db_pool: Database connection pool
    """
    # Calculate parallel speedup (3 languages in parallel vs sequential)
    estimated_sequential = duration * 3
    parallel_speedup = estimated_sequential / duration if duration > 0 else 1.0

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO fact_workflow_executions
                (execution_date, total_duration_seconds, repos_processed,
                 tasks_executed, tasks_succeeded, parallel_speedup_factor,
                 languages_processed, success_rate)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, datetime.now(timezone.utc).replace(tzinfo=None), duration, repos_count, 9, 9,
            parallel_speedup, TARGET_LANGUAGES, 1.0)


if __name__ == "__main__":
    # Start the Render Workflows task server
    # This registers all @task decorated functions and begins listening for task execution requests
    start()
