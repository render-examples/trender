"""
Shared Resource Management
Handles initialization and cleanup of shared resources like GitHub API client and database pool.
"""

import asyncpg
import os
from github_api import GitHubAPIClient


async def init_connections():
    """
    Initialize shared GitHub API client and database connection pool.

    Returns:
        Tuple of (GitHubAPIClient, asyncpg.Pool)
    """
    # Initialize GitHub API client with OAuth access token
    github_access_token = os.getenv('GITHUB_ACCESS_TOKEN')
    
    if not github_access_token:
        raise ValueError("GITHUB_ACCESS_TOKEN environment variable is required")

    github_api = GitHubAPIClient(access_token=github_access_token)
    await github_api.__aenter__()

    # Initialize database connection pool
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    pool_size_min = int(os.getenv('DATABASE_POOL_MIN_SIZE', '5'))
    pool_size_max = int(os.getenv('DATABASE_POOL_MAX_SIZE', '20'))

    db_pool = await asyncpg.create_pool(
        database_url,
        min_size=pool_size_min,
        max_size=pool_size_max
    )

    return github_api, db_pool


async def cleanup_connections(github_api: GitHubAPIClient, db_pool: asyncpg.Pool):
    """
    Clean up shared resources.

    Args:
        github_api: GitHub API client instance
        db_pool: Database connection pool
    """
    if github_api:
        await github_api.close()

    if db_pool:
        await db_pool.close()
