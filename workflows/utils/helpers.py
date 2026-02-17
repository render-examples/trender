"""
Helper utility functions for workflow execution.
"""

import sys
import asyncio
import logging
from typing import Dict, List, Tuple
import asyncpg

from connections import init_connections
from github_api import GitHubAPIClient

logger = logging.getLogger(__name__)


def chunk_list(items: List, size: int) -> List[List]:
    """Split a list into chunks of specified size."""
    return [items[i:i + size] for i in range(0, len(items), size)]


async def init_connections_with_error_handling() -> Tuple[GitHubAPIClient, asyncpg.Pool]:
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


async def fetch_readmes_parallel(
    repos: List[Dict],
    github_api: GitHubAPIClient
) -> Dict[str, str]:
    """
    Fetch README files for multiple repositories in parallel.

    Args:
        repos: List of repository dictionaries with 'full_name' key
        github_api: GitHub API client instance

    Returns:
        Dictionary mapping repo full_name to README content
    """
    readme_contents = {}
    readme_tasks = []

    for repo in repos:
        owner, name = repo.get('full_name', '/').split('/')
        readme_tasks.append(github_api.fetch_readme(owner, name))

    readme_results = await asyncio.gather(*readme_tasks, return_exceptions=True)

    for i, repo in enumerate(repos):
        if not isinstance(readme_results[i], Exception) and readme_results[i]:
            readme_contents[repo.get('full_name')] = readme_results[i]

    return readme_contents
