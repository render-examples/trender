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
from render_detection import detect_render_usage, store_render_enrichment
from etl.extract import store_raw_repos, store_raw_metrics
from etl.data_quality import calculate_data_quality_score


# Helper functions
def chunk_list(items: List, size: int) -> List[List]:
    """Split a list into chunks of specified size."""
    return [items[i:i + size] for i in range(0, len(items), size)]


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
    - 1 Render ecosystem fetch

    Returns execution summary.
    """
    # #region agent log
    import json
    import sys
    debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"workflow.py:54","message":"main_analysis_task ENTRY","data":{"dev_mode":DEV_MODE},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H4,H5"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    execution_start = datetime.now(timezone.utc)
    logger.info(f"Workflow started at {execution_start}")

    try:
        if DEV_MODE:
            # Development mode: Python only + ETL pipeline
            logger.info("DEV_MODE enabled - running Python task only")
            python_result = await fetch_language_repos('Python')
            
            logger.info("Python task completed, starting ETL pipeline")
            
            # #region agent log
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"location":"workflow.py:66","message":"About to call init_connections for ETL","data":{},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H5"}) + '\n')
            except Exception:
                pass
            # #endregion
            
            # Initialize connections for ETL pipeline
            try:
                github_api, db_pool = await init_connections()
                logger.info("Connections initialized for ETL pipeline")
            except ConnectionError as e:
                # #region agent log
                try:
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"location":"workflow.py:75","message":"ConnectionError caught in main_analysis_task","data":{"error_msg":str(e),"error_type":type(e).__name__},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H5"}) + '\n')
                except Exception:
                    pass
                # #endregion
                
                logger.error(f"FATAL: Cannot connect to database: {e}")
                logger.error("Exiting workflow gracefully due to connection failure")
                
                # Exit gracefully with error status
                sys.exit(1)
            
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

            # Execute language analysis and Render repos fetch in parallel
            results = await asyncio.gather(
                *language_tasks,
                fetch_render_repos(),
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
            try:
                github_api, db_pool = await init_connections()
                logger.info("Connections initialized for aggregation")
            except ConnectionError as e:
                # #region agent log
                try:
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"location":"workflow.py:108","message":"ConnectionError in production mode aggregation","data":{"error_msg":str(e)},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H5"}) + '\n')
                except Exception:
                    pass
                # #endregion
                
                logger.error(f"FATAL: Cannot connect to database for aggregation: {e}")
                logger.error("Exiting workflow gracefully due to connection failure")
                sys.exit(1)
            
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
    # #region agent log
    import json
    import sys
    debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"workflow.py:135","message":"fetch_language_repos ENTRY","data":{"language":language},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H5"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    logger.info(f"fetch_language_repos START for {language}")
    
    # Initialize connections for this task
    try:
        github_api, db_pool = await init_connections()
    except ConnectionError as e:
        # #region agent log
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"workflow.py:145","message":"ConnectionError in fetch_language_repos","data":{"language":language,"error_msg":str(e)},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H5"}) + '\n')
        except Exception:
            pass
        # #endregion
        
        logger.error(f"FATAL: Cannot connect to database for {language}: {e}")
        logger.error("Exiting workflow gracefully due to connection failure")
        sys.exit(1)
    
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

        # Apply DEV_MODE limits
        repo_limit = DEV_REPO_LIMIT if DEV_MODE else 50
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
        # Pass README contents to avoid duplicate API calls
        batch_results = await analyze_repo_batch(repos[:repo_limit], readme_contents)
        
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
        # #region agent log
        import json
        debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"workflow.py:204","message":"ConnectionError in analyze_repo_batch","data":{"error_msg":str(e)},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H5"}) + '\n')
        except Exception:
            pass
        # #endregion
        
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
            # #region agent log
            import json
            debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"location":"workflow.py:298","message":"Starting batch processing","data":{"batch_idx":batch_idx,"batch_size":len(batch),"repo_names":[r.get('full_name') for r in batch],"pool_size":db_pool.get_size(),"pool_idle":db_pool.get_idle_size()},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H2,H5"}) + '\n')
            except Exception:
                pass
            # #endregion
            
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
    # Validate repo_full_name exists
    repo_full_name = repo.get('full_name')
    if not repo_full_name or '/' not in repo_full_name:
        logger.warning(f"Skipping repo with invalid full_name: {repo_full_name}")
        return None
    
    owner, name = repo_full_name.split('/', 1)

    # Fetch Render usage detection (no need for commits/issues/contributors)
    # #region agent log
    import json
    import time
    debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"workflow.py:355","message":"Starting API calls","data":{"repo":repo_full_name,"has_readme":readme_content is not None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H6"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    if readme_content is not None:
        # README already fetched, don't call API again
        try:
            render_data = await detect_render_usage(repo, github_api, db_pool)
        except Exception as e:
            # #region agent log
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"location":"workflow.py:358","message":"detect_render_usage exception","data":{"repo":repo_full_name,"error_type":type(e).__name__,"error_msg":str(e)[:200]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H6"}) + '\n')
            except Exception:
                pass
            # #endregion
            render_data = {}
        
        readme = readme_content
    else:
        # Fetch README along with Render detection
        render_data, readme = await asyncio.gather(
            detect_render_usage(repo, github_api, db_pool),
            github_api.fetch_readme(owner, name),
            return_exceptions=True
        )
        
        # #region agent log
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"workflow.py:369","message":"API calls completed","data":{"repo":repo_full_name,"render_is_exception":isinstance(render_data, Exception),"readme_is_exception":isinstance(readme, Exception),"render_error":str(render_data)[:200] if isinstance(render_data, Exception) else None,"readme_error":str(readme)[:200] if isinstance(readme, Exception) else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H6"}) + '\n')
        except Exception:
            pass
        # #endregion
        
        # Handle exceptions
        render_data = render_data if not isinstance(render_data, Exception) else {}
        readme = readme if not isinstance(readme, Exception) else None

    # Build enriched repo data
    enriched = {
        'repo_full_name': repo.get('full_name'),
        'repo_url': repo.get('html_url'),
        'language': repo.get('language'),
        'description': repo.get('description'),
        'readme_content': readme,
        'stars': repo.get('stargazers_count', 0),
        'created_at': repo.get('created_at'),
        'updated_at': repo.get('updated_at'),
        'uses_render': render_data.get('uses_render', False),
        **render_data
    }
    
    # #region agent log
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"workflow.py:415","message":"enriched repo data built","data":{"repo":repo_full_name,"initial_uses_render":repo.get('uses_render',False),"render_data_uses_render":render_data.get('uses_render',False),"final_uses_render":enriched['uses_render']},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H3,H4"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    # Parse ISO datetime strings to timezone-aware datetime objects for PostgreSQL
    # GitHub API returns ISO 8601 with 'Z' suffix (UTC timezone)
    # Keep timezone-aware for TIMESTAMPTZ columns
    if isinstance(enriched['created_at'], str):
        enriched['created_at'] = datetime.fromisoformat(enriched['created_at'].replace('Z', '+00:00'))
    if isinstance(enriched['updated_at'], str):
        enriched['updated_at'] = datetime.fromisoformat(enriched['updated_at'].replace('Z', '+00:00'))

    # Calculate data quality score
    enriched['data_quality_score'] = calculate_data_quality_score(enriched)

    # Store in staging layer
    logger.info(f"Storing {enriched['repo_full_name']} to staging (quality: {enriched['data_quality_score']})")
    await store_in_staging(enriched, db_pool)
    
    # If Render repo, store enrichment data
    if enriched.get('uses_render') and render_data.get('uses_render'):
        enriched_project = {
            'repo_full_name': enriched['repo_full_name'],
            'render_category': render_data.get('render_category', 'community'),
            'render_services': render_data.get('services', []),
            'has_blueprint_button': render_data.get('has_blueprint_button', False),
            'render_complexity_score': render_data.get('complexity_score', 0),
            'service_count': render_data.get('service_count', 0)
        }
        logger.info(f"Storing Render enrichment for {enriched['repo_full_name']}")
        await store_render_enrichment([enriched_project], db_pool)
    
    logger.info(f"Successfully stored {enriched['repo_full_name']} to staging")

    # Return minimal summary (data is already in DB, no need to pass full objects)
    return {
        'repo_full_name': enriched['repo_full_name'],
        'language': enriched['language'],
        'stars': enriched['stars']
    }


async def store_in_staging(repo: Dict, db_pool: asyncpg.Pool):
    """Store enriched repository data in staging layer."""
    # #region agent log
    import json
    import time
    debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"workflow.py:454","message":"store_in_staging ENTRY","data":{"repo":repo.get('repo_full_name'),"uses_render":repo.get('uses_render',False),"quality_score":repo.get('data_quality_score',0.0)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H1,H3"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO stg_repos_validated
                (repo_full_name, repo_url, language, description, stars,
                 created_at, updated_at, uses_render,
                 readme_content, data_quality_score)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (repo_full_name) DO UPDATE SET
                stars = EXCLUDED.stars,
                updated_at = EXCLUDED.updated_at,
                uses_render = EXCLUDED.uses_render,
                readme_content = EXCLUDED.readme_content,
                data_quality_score = EXCLUDED.data_quality_score,
                loaded_at = NOW()
        """, repo.get('repo_full_name'), repo.get('repo_url'), repo.get('language'),
            repo.get('description'), repo.get('stars', 0),
            repo.get('created_at'), repo.get('updated_at'),
            repo.get('uses_render', False),
            repo.get('readme_content'), repo.get('data_quality_score', 0.0))
        
        # #region agent log
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"workflow.py:474","message":"store_in_staging COMPLETE","data":{"repo":repo.get('repo_full_name')},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H1,H3,H5"}) + '\n')
        except Exception:
            pass
        # #endregion


@task
async def fetch_render_repos() -> List[Dict]:
    """
    Fetch Render ecosystem repos using multi-strategy search.
    Combines path search, render-examples org, and topic search.
    
    Returns:
        List of repository dictionaries
    """
    # #region agent log
    import json
    import sys
    debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"workflow.py:400","message":"fetch_render_repos ENTRY","data":{},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H5"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    logger.info("fetch_render_repos START - multi-strategy search")
    
    # Initialize connections
    try:
        github_api, db_pool = await init_connections()
    except ConnectionError as e:
        # #region agent log
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"workflow.py:410","message":"ConnectionError in fetch_render_repos","data":{"error_msg":str(e)},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H5"}) + '\n')
        except Exception:
            pass
        # #endregion
        
        logger.error(f"FATAL: Cannot connect to database for render repos: {e}")
        logger.error("Exiting workflow gracefully due to connection failure")
        sys.exit(1)
    
    try:
        # Multi-strategy search: path + org + topic
        repos = await github_api.search_render_ecosystem(limit=50)
        logger.info(f"Found {len(repos)} total Render ecosystem repos")
        
        if not repos:
            return []
        
        # Mark all as Render projects
        for repo in repos:
            repo['uses_render'] = True
        
        # #region agent log
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"workflow.py:528","message":"fetch_render_repos - marked repos as Render","data":{"count":len(repos),"sample_repos":[r.get('full_name') for r in repos[:5]]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H4"}) + '\n')
        except Exception:
            pass
        # #endregion
        
        # Store in raw layer
        await store_raw_repos(repos, db_pool, source_type='render_ecosystem')
        
        # Analyze batch (stores in staging)
        analyzed = await analyze_repo_batch(repos)
        
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
        # #region agent log
        import json
        import time
        debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
        
        # Check what's in staging BEFORE extraction
        staging_count = await conn.fetchval("SELECT COUNT(*) FROM stg_repos_validated WHERE uses_render = TRUE")
        staging_render_repos = await conn.fetch("SELECT repo_full_name, uses_render, data_quality_score FROM stg_repos_validated WHERE uses_render = TRUE LIMIT 10")
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"workflow.py:559","message":"aggregate_results - staging state","data":{"render_repos_in_staging":staging_count,"sample_repos":[dict(r) for r in staging_render_repos]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H1,H2,H3"}) + '\n')
        except Exception:
            pass
        # #endregion
        
        # Extract all high-quality repos from staging (no date filtering)
        # Join with render enrichment to get full data
        # Pull top 50 per language = 150 total repos
        repos = await conn.fetch("""
            SELECT
                srv.repo_full_name,
                srv.repo_url,
                srv.language,
                srv.description,
                srv.stars,
                srv.created_at,
                srv.updated_at,
                srv.uses_render,
                srv.readme_content,
                srv.data_quality_score,
                sre.render_category,
                sre.render_services,
                sre.render_complexity_score,
                sre.has_blueprint_button,
                sre.service_count
            FROM stg_repos_validated srv
            LEFT JOIN stg_render_enrichment sre ON srv.repo_full_name = sre.repo_full_name
            WHERE srv.data_quality_score >= 0.70
            ORDER BY srv.stars DESC
            LIMIT 150
        """)
        
        # #region agent log
        render_repos_extracted = sum(1 for r in repos if r.get('uses_render'))
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"workflow.py:588","message":"aggregate_results - extraction complete","data":{"total_extracted":len(repos),"render_repos_extracted":render_repos_extracted},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H2"}) + '\n')
        except Exception:
            pass
        # #endregion
        
        logger.info(f"Extracted {len(repos)} recent repos from staging")
        
        if not repos:
            logger.warning("No repos found in staging for analytics")
            return {
                'repos_processed': 0,
                'execution_time': (datetime.now(timezone.utc) - execution_start).total_seconds(),
                'success': True
            }
        
        # Load to analytics (consolidated logic)
        await load_to_analytics_simple(repos, conn)
        
        # region agent log
        import json
        import time
        debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
        
        # Check analytics tables AFTER load
        analytics_render_count = await conn.fetchval("SELECT COUNT(*) FROM dim_repositories WHERE is_current = TRUE AND uses_render = TRUE")
        analytics_render_repos = await conn.fetch("SELECT repo_full_name, uses_render, language FROM dim_repositories WHERE is_current = TRUE AND uses_render = TRUE LIMIT 10")
        
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"workflow.py:609","message":"aggregate_results - analytics state AFTER load","data":{"render_repos_in_analytics":analytics_render_count,"sample_repos":[dict(r) for r in analytics_render_repos]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H1"}) + '\n')
        except Exception:
            pass
        # endregion
        
        return {
            'repos_processed': len(repos),
            'execution_time': (datetime.now(timezone.utc) - execution_start).total_seconds(),
            'success': True
        }


async def load_to_analytics_simple(repos: List, conn: asyncpg.Connection):
    """
    Simplified load: upsert dimensions and facts with star-recency scoring.
    
    Scoring formula:
    - 50% normalized star count
    - 50% recency score (based on repo creation date within last 3 months)
    
    Args:
        repos: List of repository records from staging
        conn: Database connection
    """
    # region agent log
    lang_counts = {}
    for r in repos:
        lang_counts[r.get('language', 'NULL')] = lang_counts.get(r.get('language', 'NULL'), 0) + 1
    logger.info(f"[DEBUG-A] load_to_analytics_simple ENTRY: total_repos={len(repos)}, lang_breakdown={lang_counts}")
    # endregion
    
    today = date.today()
    now = datetime.now(timezone.utc)
    
    # region agent log
    successful_loads = {'Python': 0, 'TypeScript': 0, 'Go': 0, 'Other': 0}
    failed_loads = {'Python': 0, 'TypeScript': 0, 'Go': 0, 'Other': 0}
    # endregion
    
    # Calculate max stars for normalization (separately for general and Render repos)
    general_repos = [r for r in repos if not r.get('uses_render', False)]
    render_repos = [r for r in repos if r.get('uses_render', False)]
    
    max_stars_general = max([r.get('stars', 1) for r in general_repos]) if general_repos else 1
    max_stars_render = max([r.get('stars', 1) for r in render_repos]) if render_repos else 1
    
    logger.info(f"Max stars - General: {max_stars_general}, Render: {max_stars_render}")
    
    def calculate_recency_score(created_at) -> float:
        """Calculate recency score based on repo age."""
        if not created_at:
            return 0.0
        
        # Ensure created_at is timezone-aware
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        age_days = (now - created_at).days
        
        if age_days <= 30:
            return 1.0
        elif age_days <= 60:
            return 0.75
        elif age_days <= 90:
            return 0.5
        else:
            return 0.0
    
    for idx, repo in enumerate(repos, 1):
        repo_name = repo['repo_full_name']
        if not repo_name:
            continue
        
        # region agent log
        repo_lang = repo.get('language', 'NULL')
        # endregion
        
        try:
            # Upsert into dim_repositories (simplified, no SCD Type 2)
            await conn.execute("""
                INSERT INTO dim_repositories
                    (repo_full_name, repo_url, description, readme_content, language, 
                     created_at, uses_render, render_category, valid_from, is_current)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), TRUE)
                ON CONFLICT (repo_full_name) 
                WHERE is_current = TRUE
                DO UPDATE SET
                    repo_url = EXCLUDED.repo_url,
                    description = EXCLUDED.description,
                    readme_content = EXCLUDED.readme_content,
                    uses_render = EXCLUDED.uses_render
            """, repo_name, repo['repo_url'], repo['description'],
                repo['readme_content'], repo['language'], repo['created_at'],
                repo['uses_render'], 'community')
            
            # Get keys for fact table
            repo_key = await conn.fetchval("""
                SELECT repo_key FROM dim_repositories
                WHERE repo_full_name = $1 AND is_current = TRUE
            """, repo_name)
            
            language_key = await conn.fetchval("""
                SELECT language_key FROM dim_languages
                WHERE language_name = $1
            """, repo['language'])
            
            # region agent log
            logger.info(f"[DEBUG-C] Key lookup: repo={repo_name}, lang={repo_lang}, repo_key={repo_key}, lang_key={language_key}")
            # endregion
            
            if not repo_key or not language_key:
                # region agent log
                lang_bucket = repo_lang if repo_lang in ['Python', 'TypeScript', 'Go'] else 'Other'
                failed_loads[lang_bucket] += 1
                logger.warning(f"[DEBUG-A,C] SKIP: Missing key for repo={repo_name}, lang={repo_lang}, repo_key={repo_key}, lang_key={language_key}")
                # endregion
                continue
            
            # Calculate momentum score using star-recency formula
            stars = repo.get('stars', 0)
            uses_render = repo.get('uses_render', False)
            
            # Normalize stars based on appropriate max (general vs render)
            max_stars = max_stars_render if uses_render else max_stars_general
            normalized_stars = stars / max_stars if max_stars > 0 else 0.0
            
            # Calculate recency score
            recency_score = calculate_recency_score(repo.get('created_at'))
            
            # Final momentum score: 50% stars + 50% recency
            momentum_score = (normalized_stars * 0.5) + (recency_score * 0.5)
            
            logger.info(f"Score for {repo_name}: stars={stars}, norm_stars={normalized_stars:.3f}, recency={recency_score}, momentum={momentum_score:.3f}")
            
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
            if uses_render and repo.get('render_services'):
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
            
            # region agent log
            lang_bucket = repo_lang if repo_lang in ['Python', 'TypeScript', 'Go'] else 'Other'
            successful_loads[lang_bucket] += 1
            # endregion
        except Exception as e:
            # region agent log
            lang_bucket = repo_lang if repo_lang in ['Python', 'TypeScript', 'Go'] else 'Other'
            failed_loads[lang_bucket] += 1
            logger.error(f"[DEBUG-A,C] EXCEPTION loading repo={repo_name}, lang={repo_lang}: {type(e).__name__}: {e}")
            # endregion
            continue
    
    # region agent log
    logger.info(f"[DEBUG-A,B] load_to_analytics_simple EXIT: successful={successful_loads}, failed={failed_loads}, total={len(repos)}")
    # endregion
    
    logger.info(f"Loaded {len(repos)} repos to analytics layer")


if __name__ == "__main__":
    # Start the Render Workflows task server
    # This registers all @task decorated functions and begins listening for task execution requests
    start()
