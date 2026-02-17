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
import uuid
import json
from datetime import datetime, timedelta, date, timezone
from typing import Dict, List, Optional

# Ensure the workflows directory is in the Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connections import init_connections, cleanup_connections
from github_api import GitHubAPIClient
from etl.extract import store_raw_repos

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


# ============================================================================
# Helper Functions
# ============================================================================

def chunk_list(items: List, size: int) -> List[List]:
    """Split a list into chunks of specified size."""
    return [items[i:i + size] for i in range(0, len(items), size)]


# ============================================================================
# Workflow Tracing
# ============================================================================

class WorkflowTrace:
    """
    Helper class to track workflow execution with hierarchical task timing.
    
    Provides structured logging of task execution for observability.
    Stores execution traces in the database for debugging and visualization.
    """
    
    def __init__(self, run_id: Optional[str] = None):
        """Initialize a new workflow trace with a unique run ID."""
        self.run_id = run_id or f"wfr_{uuid.uuid4().hex[:12]}"
        self.started_at = datetime.now(timezone.utc)
        self.completed_at = None
        self.status = 'running'
        self.task_tree = {
            'name': 'main_analysis_task',
            'started_at': self.started_at.isoformat(),
            'completed_at': None,
            'status': 'running',
            'children': []
        }
        self.repos_processed = 0
        self.error_message = None
    
    def add_task(self, task_name: str, language: Optional[str] = None) -> Dict:
        """Add a new top-level task to the tree and return its reference."""
        task = {
            'name': task_name,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None,
            'status': 'running',
            'children': []
        }
        if language:
            task['language'] = language
        self.task_tree['children'].append(task)
        return task
    
    def complete_task(self, task_ref: Dict, status: str = 'completed'):
        """Mark a task as completed with the given status."""
        task_ref['completed_at'] = datetime.now(timezone.utc).isoformat()
        task_ref['status'] = status
    
    def add_subtask(self, parent_task: Dict, subtask_name: str) -> Dict:
        """Add a subtask under a parent task (for nested task hierarchies)."""
        subtask = {
            'name': subtask_name,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None,
            'status': 'running',
        }
        parent_task['children'].append(subtask)
        return subtask
    
    def complete(self, status: str = 'completed', error_message: Optional[str] = None):
        """Mark the entire workflow as completed."""
        self.completed_at = datetime.now(timezone.utc)
        self.status = status
        self.error_message = error_message
        self.task_tree['completed_at'] = self.completed_at.isoformat()
        self.task_tree['status'] = status
    
    async def persist(self, db_pool: asyncpg.Pool):
        """
        Persist the workflow trace to the database.
        
        Note: Failures during persistence are logged but don't fail the workflow.
        This ensures tracing issues don't impact the main ETL pipeline.
        """
        try:
            execution_time = (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at else None
            )
            
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO fact_workflow_runs
                        (run_id, started_at, completed_at, status, task_tree,
                         error_message, repos_processed, execution_time_seconds)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (run_id) DO UPDATE SET
                        completed_at = EXCLUDED.completed_at,
                        status = EXCLUDED.status,
                        task_tree = EXCLUDED.task_tree,
                        error_message = EXCLUDED.error_message,
                        repos_processed = EXCLUDED.repos_processed,
                        execution_time_seconds = EXCLUDED.execution_time_seconds
                """, self.run_id, self.started_at, self.completed_at, self.status,
                    json.dumps(self.task_tree), self.error_message,
                    self.repos_processed, execution_time)
            
            logger.info(f"Workflow trace persisted: {self.run_id} ({self.status})")
        except Exception as e:
            logger.error(f"Failed to persist workflow trace: {e}")
            # Don't fail the workflow if tracing fails


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


def _process_task_result(result, index: int, target_languages: List[str], trace: WorkflowTrace):
    """Process a single task result and update trace."""
    # Determine task name and language
    is_language_task = index < len(target_languages)
    task_name = target_languages[index] if is_language_task else 'fetch_render_repos'
    language = task_name if is_language_task else None
    
    # Handle exceptions
    if isinstance(result, Exception):
        logger.error(f"Task {index} ({task_name}) FAILED: {type(result).__name__}: {str(result)}")
        logger.error("".join(traceback.format_exception(type(result), result, result.__traceback__)))
        task_ref = trace.add_task('fetch_language_repos' if language else 'fetch_render_repos', language=language)
        trace.complete_task(task_ref, 'failed')
        return
    
    # Handle successful results
    result_len = len(result.get('repos', [])) if isinstance(result, dict) else 'N/A'
    logger.info(f"Task {index} ({task_name}) SUCCESS: {type(result).__name__}, items={result_len}")
    
    if isinstance(result, dict):
        task_ref = trace.add_task('fetch_language_repos' if language else 'fetch_render_repos', language=language)
        task_ref['started_at'] = result.get('started_at', task_ref['started_at'])
        task_ref['completed_at'] = result.get('completed_at')
        task_ref['status'] = 'completed'
        
        # Add subtasks from the result to the trace
        for subtask_timing in result.get('subtasks', []):
            subtask = trace.add_subtask(task_ref, subtask_timing['task_name'])
            subtask['started_at'] = subtask_timing['started_at']
            subtask['completed_at'] = subtask_timing['completed_at']
            subtask['status'] = subtask_timing['status']


def _add_task_to_trace(result: Dict, trace: WorkflowTrace, language: Optional[str] = None):
    """Add a completed task and its subtasks to the trace."""
    task_ref = trace.add_task('fetch_language_repos', language=language)
    task_ref['started_at'] = result.get('started_at', task_ref['started_at'])
    task_ref['completed_at'] = result.get('completed_at')
    task_ref['status'] = 'completed'
    
    for subtask_timing in result.get('subtasks', []):
        subtask = trace.add_subtask(task_ref, subtask_timing['task_name'])
        subtask['started_at'] = subtask_timing['started_at']
        subtask['completed_at'] = subtask_timing['completed_at']
        subtask['status'] = subtask_timing['status']


# ============================================================================
# Main Workflow Task
# ============================================================================


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
    
    # Initialize workflow trace
    trace = WorkflowTrace()
    logger.info(f"Workflow trace initialized: {trace.run_id}")

    try:
        if DEV_MODE:
            # Development mode: Python only + ETL pipeline
            logger.info("DEV_MODE enabled - running Python task only")
            python_result = await fetch_language_repos('Python')
            _add_task_to_trace(python_result, trace, language='Python')
            logger.info("Python task completed, starting ETL pipeline")
            
            github_api, db_pool = await init_connections_with_error_handling()
            aggregate_task = trace.add_task('aggregate_results')
            final_result = await aggregate_results([python_result], db_pool, execution_start, trace)
            trace.complete_task(aggregate_task)
            
            execution_time = (datetime.now(timezone.utc) - execution_start).total_seconds()
            logger.info(f"DEV_MODE workflow completed in {execution_time}s")
            
            trace.repos_processed = final_result.get('repos_processed', 0)
            trace.complete('completed')
            await trace.persist(db_pool)
            
            final_result.update({
                'dev_mode': True,
                'languages': ['Python'],
                'trace_id': trace.run_id
            })
            return final_result
        else:
            # Production mode: Full pipeline
            language_tasks = [fetch_language_repos(lang) for lang in TARGET_LANGUAGES]
            logger.info(f"Created {len(language_tasks)} language tasks for {TARGET_LANGUAGES}")

            results = await asyncio.gather(*language_tasks, fetch_render_repos(), return_exceptions=True)

            # Process results and update trace
            logger.info(f"Parallel tasks completed. Total results: {len(results)}")
            for i, result in enumerate(results):
                _process_task_result(result, i, TARGET_LANGUAGES, trace)

            # Aggregate and store final results
            github_api, db_pool = await init_connections_with_error_handling()
            aggregate_task = trace.add_task('aggregate_results')
            final_result = await aggregate_results(results, db_pool, execution_start, trace)
            trace.complete_task(aggregate_task)
            
            trace.repos_processed = final_result.get('repos_processed', 0)
            trace.complete('completed')
            await trace.persist(db_pool)
            final_result['trace_id'] = trace.run_id
            return final_result
    except Exception as e:
        # Mark trace as failed and persist
        trace.complete('failed', error_message=str(e))
        try:
            # Try to get db_pool if available
            if 'db_pool' in locals():
                await trace.persist(db_pool)
        except Exception:
            pass
        raise
    finally:
        # Cleanup if connections were initialized
        try:
            await cleanup_connections(github_api, db_pool)
        except Exception:
            pass  # Connections may not have been initialized if error occurred early


# ============================================================================
# Parallel Task Functions
# ============================================================================

@task
async def fetch_language_repos(language: str) -> Dict:
    """
    Fetch and store trending repos for a specific language.

    Args:
        language: Programming language to fetch

    Returns:
        Dict with structure:
        {
            'repos': List of enriched repository dictionaries,
            'subtasks': List of timing metadata from subtasks,
            'started_at': ISO timestamp string,
            'completed_at': ISO timestamp string
        }
    """
    start_time = datetime.now(timezone.utc)
    logger.info(f"Fetching {language} repositories")
    
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
            return {
                'repos': [],
                'subtasks': []
            }

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
        
        end_time = datetime.now(timezone.utc)
        logger.info(f"Fetched {len(batch_results['enriched_repos'])} {language} repos")
        return {
            'repos': batch_results['enriched_repos'],
            'subtasks': [batch_results['timing']],
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat()
        }
    finally:
        # Cleanup connections
        await cleanup_connections(github_api, db_pool)


@task
async def analyze_repo_batch(repos: List[Dict], readme_contents: Dict[str, str] = None) -> Dict:
    """
    Analyze a batch of repositories with detailed metrics.
    
    This task runs independently and initializes its own connections.

    Args:
        repos: List of repository dictionaries (JSON-serializable)
        readme_contents: Optional dict mapping repo_full_name to README content (to avoid duplicate API calls)

    Returns:
        Dict with structure:
        {
            'enriched_repos': List of enriched repository dictionaries,
            'timing': {
                'task_name': 'analyze_repo_batch',
                'started_at': ISO timestamp string,
                'completed_at': ISO timestamp string,
                'status': 'completed' or 'failed'
            }
        }
    """
    start_time = datetime.now(timezone.utc)
    logger.info(f"analyze_repo_batch: Processing {len(repos)} repos")
    readme_contents = readme_contents or {}
    
    # Initialize connections for this independent task
    try:
        github_api, db_pool = await init_connections()
    except (ConnectionError, Exception) as e:
        logger.error(f"Failed to initialize connections: {type(e).__name__}: {str(e)}")
        end_time = datetime.now(timezone.utc)
        return {
            'enriched_repos': [],
            'timing': {
                'task_name': 'analyze_repo_batch',
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'status': 'failed'
            }
        }
    
    try:
        enriched_repos = []

        # Process repos in batches of 10
        for batch_idx, batch in enumerate(chunk_list(repos, size=10)):
            batch_tasks = [
                analyze_single_repo(repo, github_api, db_pool, readme_contents.get(repo.get('full_name')))
                for repo in batch
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Filter out exceptions and collect successful results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    repo_name = batch[i].get('full_name', 'unknown')
                    logger.error(f"Failed to analyze {repo_name}: {type(result).__name__}: {str(result)}")
                elif result is not None:
                    enriched_repos.append(result)

        logger.info(f"analyze_repo_batch: Completed with {len(enriched_repos)} enriched repos")
        end_time = datetime.now(timezone.utc)
        return {
            'enriched_repos': enriched_repos,
            'timing': {
                'task_name': 'analyze_repo_batch',
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'status': 'completed'
            }
        }
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
    await store_in_staging(enriched, db_pool)

    # Return minimal summary (data is already in DB, no need to pass full objects)
    return {
        'repo_full_name': enriched['repo_full_name'],
        'language': enriched['language'],
        'stars': enriched['stars']
    }


# ============================================================================
# Helper Functions for Data Processing
# ============================================================================

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
async def fetch_render_repos() -> Dict:
    """
    Fetch independent Render projects using code search.
    Searches for repositories with render.yaml in root directory.
    All repos are assigned language='render' (lowercase) for identification.
    
    Returns:
        Dict with structure:
        {
            'repos': List of repository dictionaries,
            'subtasks': List of timing metadata from subtasks,
            'started_at': ISO timestamp string,
            'completed_at': ISO timestamp string
        }
    """
    start_time = datetime.now(timezone.utc)
    logger.info("Searching for render.yaml repositories")
    
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
            return {
                'repos': [],
                'subtasks': []
            }
        
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
        
        end_time = datetime.now(timezone.utc)
        logger.info(f"Found {len(analyzed['enriched_repos'])} Render repos")
        return {
            'repos': analyzed['enriched_repos'],
            'subtasks': [analyzed['timing']],
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat()
        }
        
    finally:
        await cleanup_connections(github_api, db_pool)


async def cleanup_old_data(db_pool: asyncpg.Pool) -> Dict[str, int]:
    """
    Execute tiered data retention cleanup.
    
    Retention policy:
    - Raw layer: 7 days (debugging and reprocessing)
    - Staging layer: 7 days (ETL audit trail)
    - Analytics layer: 30 days (trending analysis)
    
    Args:
        db_pool: Database connection pool
        
    Returns:
        Dictionary with cleanup statistics per table
    """
    logger.info("Starting data retention cleanup...")
    
    # Read SQL cleanup script
    script_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'data_retention_cleanup.sql')
    
    try:
        with open(script_path, 'r') as f:
            cleanup_sql = f.read()
    except FileNotFoundError:
        logger.error(f"Cleanup script not found at {script_path}")
        return {'error': 'Script not found'}
    except IOError as e:
        logger.error(f"Failed to read cleanup script: {e}")
        return {'error': f'Failed to read script: {str(e)}'}
    
    cleanup_stats = {}
    
    try:
        async with db_pool.acquire() as conn:
            # Execute cleanup script
            # Note: The script uses a transaction, so it's atomic
            # Use execute() instead of fetch() to support multi-statement scripts
            await conn.execute(cleanup_sql)
            
            # Query row counts after cleanup
            tables = [
                'raw_github_repos',
                'raw_repo_metrics', 
                'stg_render_enrichment',
                'stg_repos_validated',
                'fact_repo_snapshots',
                'fact_render_usage'
            ]
            
            for table in tables:
                try:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    cleanup_stats[table] = count
                    logger.info(f"  {table}: {count} rows remaining")
                except Exception as e:
                    logger.warning(f"  {table}: Could not get count ({e})")
        
        logger.info("Data retention cleanup completed successfully")
        return cleanup_stats
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error during data retention cleanup: {type(e).__name__}: {str(e)}")
        logger.error(f"SQL State: {e.sqlstate if hasattr(e, 'sqlstate') else 'N/A'}")
        # Return error but don't fail the workflow
        return {'error': f'Database error: {str(e)}'}
    except Exception as e:
        logger.error(f"Error during data retention cleanup: {type(e).__name__}: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_exception(type(e), e, e.__traceback__))}")
        # Return error but don't fail the workflow
        return {'error': str(e)}


# ============================================================================
# ETL Pipeline Functions
# ============================================================================

async def aggregate_results(all_results: List, db_pool: asyncpg.Pool,
                            execution_start: datetime, trace: Optional[WorkflowTrace] = None) -> Dict:
    """
    Simplified ETL: Extract from staging, order by stars, load to analytics.
    
    Args:
        all_results: List of results from parallel tasks
        db_pool: Database connection pool
        execution_start: Workflow execution start time
        trace: Optional workflow trace for tracking cleanup task
    
    Returns:
        Execution summary dictionary
    """
    logger.info("Aggregating results from all tasks")
    
    # Count successful task results
    # Results are now dicts with 'repos' key, or Exceptions, or empty dicts
    successful_tasks = sum(
        1 for r in all_results 
        if not isinstance(r, Exception) and isinstance(r, dict) and len(r.get('repos', [])) > 0
    )
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
        
        # Run data retention cleanup after successful ETL
        # Note: Cleanup errors are logged but don't fail the workflow
        # This ensures ETL success even if cleanup encounters issues
        logger.info("ETL completed successfully, running data retention cleanup...")
        
        # Track cleanup task if trace is available
        cleanup_task = None
        if trace:
            cleanup_task = trace.add_task('cleanup_old_data')
        
        cleanup_stats = await cleanup_old_data(db_pool)
        
        if cleanup_task:
            # Mark as completed even if cleanup had errors (graceful degradation)
            status = 'completed' if 'error' not in cleanup_stats else 'failed'
            trace.complete_task(cleanup_task, status)
        
        # Log warning if cleanup failed but continue workflow
        if 'error' in cleanup_stats:
            logger.warning(f"Data cleanup encountered an error but workflow continues: {cleanup_stats['error']}")
        
        return {
            'repos_processed': len(repos),
            'execution_time': (datetime.now(timezone.utc) - execution_start).total_seconds(),
            'cleanup_stats': cleanup_stats,
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
            
        except Exception as e:
            logger.error(f"Error loading repo {repo_name}: {type(e).__name__}: {e}")
            continue
    
    logger.info(f"Loaded {len(repos)} repos to analytics layer")


if __name__ == "__main__":
    # Start the Render Workflows task server
    # This registers all @task decorated functions and begins listening for task execution requests
    start()
