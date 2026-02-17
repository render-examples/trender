"""
Batch repository analysis tasks.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import asyncpg

from app import app
from connections import init_connections, cleanup_connections
from github_api import GitHubAPIClient
from utils import chunk_list
from etl import store_in_staging

logger = logging.getLogger(__name__)


async def initialize_batch_connections() -> Optional[Tuple[GitHubAPIClient, asyncpg.Pool]]:
    """
    Initialize connections for batch analysis.

    Returns:
        Tuple of (GitHubAPIClient, asyncpg.Pool) if successful, None otherwise
    """
    try:
        return await init_connections()
    except (ConnectionError, Exception) as e:
        logger.error(f"Failed to initialize connections: {type(e).__name__}: {str(e)}")
        return None


def handle_batch_errors(batch: List[Dict], batch_results: List) -> List[Dict]:
    """
    Filter out exceptions and collect successful results from batch.

    Args:
        batch: List of repository dictionaries
        batch_results: Results from asyncio.gather (may include exceptions)

    Returns:
        List of successful enriched repositories
    """
    enriched_repos = []

    for i, result in enumerate(batch_results):
        if isinstance(result, Exception):
            repo_name = batch[i].get('full_name', 'unknown')
            logger.error(f"Failed to analyze {repo_name}: {type(result).__name__}: {str(result)}")
        elif result is not None:
            enriched_repos.append(result)

    return enriched_repos


async def process_repo_batch_chunk(
    batch: List[Dict],
    github_api: GitHubAPIClient,
    db_pool: asyncpg.Pool,
    readme_contents: Dict[str, str]
) -> List[Dict]:
    """
    Process a single batch chunk of repositories.

    Args:
        batch: List of repository dictionaries (max 10)
        github_api: GitHub API client
        db_pool: Database connection pool
        readme_contents: Pre-fetched README contents

    Returns:
        List of successfully enriched repositories
    """
    batch_tasks = [
        analyze_single_repo(repo, github_api, db_pool, readme_contents.get(repo.get('full_name')))
        for repo in batch
    ]

    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
    return handle_batch_errors(batch, batch_results)


@app.task
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
    connections = await initialize_batch_connections()
    if not connections:
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

    github_api, db_pool = connections

    try:
        enriched_repos = []

        # Process repos in batches of 10
        for batch_idx, batch in enumerate(chunk_list(repos, size=10)):
            batch_enriched = await process_repo_batch_chunk(
                batch, github_api, db_pool, readme_contents
            )
            enriched_repos.extend(batch_enriched)

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


async def analyze_single_repo(
    repo: Dict,
    github_api: GitHubAPIClient,
    db_pool: asyncpg.Pool,
    readme_content: str = None
) -> Dict:
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
