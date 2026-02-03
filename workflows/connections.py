"""
Shared Resource Management
Handles initialization and cleanup of shared resources like GitHub API client and database pool.
"""

import asyncpg
import asyncio
import os
from github_api import GitHubAPIClient


async def init_connections():
    """
    Initialize shared GitHub API client and database connection pool with error handling.
    
    Returns:
        Tuple of (GitHubAPIClient, asyncpg.Pool)
        
    Raises:
        ValueError: If required environment variables are missing
        ConnectionError: If connections cannot be established
    """
    # Validate GitHub token
    github_access_token = os.getenv('GITHUB_ACCESS_TOKEN')
    if not github_access_token:
        raise ValueError("GITHUB_ACCESS_TOKEN environment variable is required")
    
    if not github_access_token.startswith(('ghp_', 'gho_', 'github_pat_')):
        raise ValueError("GITHUB_ACCESS_TOKEN appears invalid (wrong format)")
    
    # Initialize GitHub API client
    try:
        github_api = GitHubAPIClient(access_token=github_access_token)
        await github_api.__aenter__()
    except Exception as e:
        raise ConnectionError(f"Failed to initialize GitHub API client: {e}")
    
    # Validate database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    # Initialize database connection pool with retry logic
    pool_size_min = int(os.getenv('DATABASE_POOL_MIN_SIZE', '2'))
    pool_size_max = int(os.getenv('DATABASE_POOL_MAX_SIZE', '10'))
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            db_pool = await asyncpg.create_pool(
                database_url,
                min_size=pool_size_min,
                max_size=pool_size_max,
                timeout=30,
                command_timeout=60
            )
            
            # Test connection
            async with db_pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            
            return github_api, db_pool
            
        except (asyncpg.InvalidPasswordError, asyncpg.InvalidCatalogNameError, 
                asyncpg.CannotConnectNowError, Exception) as e:
            # Handle specific database errors
            match type(e).__name__:
                case 'InvalidPasswordError':
                    raise ConnectionError("Database authentication failed (wrong password)")
                case 'InvalidCatalogNameError':
                    raise ConnectionError("Database does not exist")
                case 'CannotConnectNowError':
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise ConnectionError("Database connection refused (server not accepting connections)")
                case _:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise ConnectionError(f"Failed to create database connection pool: {e}")
    
    raise ConnectionError("Failed to connect after 3 attempts")


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
