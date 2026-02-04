"""
Shared Resource Management
Handles initialization and cleanup of shared resources like GitHub API client and database pool.
"""

import asyncpg
import asyncio
import os
from github_api import GitHubAPIClient


def _validate_github_token(token: str) -> tuple[bool, str, str, str]:
    """
    Validate GitHub token format and extract OAuth credentials if needed.
    
    Returns:
        Tuple of (is_oauth, refresh_token, client_id, client_secret)
    """
    is_oauth = token.startswith('ghu_')
    is_pat = token.startswith(('ghp_', 'gho_', 'github_pat_'))
    
    if not (is_oauth or is_pat):
        raise ValueError(
            "GITHUB_ACCESS_TOKEN appears invalid (wrong format). "
            "Expected to start with 'ghp_', 'gho_', 'github_pat_', or 'ghu_'"
        )
    
    if not is_oauth:
        return False, None, None, None
    
    # OAuth token - get credentials
    refresh_token = os.getenv('GITHUB_REFRESH_TOKEN')
    client_id = os.getenv('GITHUB_CLIENT_ID')
    client_secret = os.getenv('GITHUB_CLIENT_SECRET')
    
    # Warn about missing credentials
    if not refresh_token:
        print("⚠️  WARNING: Using OAuth token without GITHUB_REFRESH_TOKEN")
        print("   OAuth tokens expire after 8 hours. Set GITHUB_REFRESH_TOKEN for auto-renewal.")
    elif not client_id or not client_secret:
        print("⚠️  WARNING: GITHUB_REFRESH_TOKEN is set but GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET is missing")
        print("   Token refresh will fail. Set both GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.")
    
    return True, refresh_token, client_id, client_secret


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
    
    _, refresh_token, client_id, client_secret = _validate_github_token(github_access_token)
    
    # Initialize GitHub API client
    try:
        github_api = GitHubAPIClient(
            access_token=github_access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret
        )
        await github_api.__aenter__()
    except Exception as e:
        raise ConnectionError(f"Failed to initialize GitHub API client: {e}")
    
    # Initialize database connection pool
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    db_pool = await _init_database_pool(database_url)
    return github_api, db_pool


async def _init_database_pool(database_url: str) -> asyncpg.Pool:
    """Initialize database connection pool with retry logic."""
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
            
            return db_pool
            
        except asyncpg.InvalidPasswordError:
            raise ConnectionError("Database authentication failed (wrong password)")
        except asyncpg.InvalidCatalogNameError:
            raise ConnectionError("Database does not exist")
        except asyncpg.CannotConnectNowError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise ConnectionError("Database connection refused (server not accepting connections)")
        except Exception as e:
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
