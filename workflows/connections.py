"""
Shared Resource Management
Handles initialization and cleanup of shared resources like GitHub API client and database pool.
"""

import os
import sys
# Ensure workflows directory is in path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncpg
import asyncio
import logging
from github_api import GitHubAPIClient
from lib.oauth_manager import OAuthCredentialManager

logger = logging.getLogger(__name__)


async def _load_oauth_credentials(oauth_manager: OAuthCredentialManager) -> str:
    """
    Load OAuth credentials from database and return access token.

    Raises:
        ValueError: If no credentials are found in the database
    """
    access_token = await oauth_manager.get_valid_token()
    logger.info("✅ Loaded GitHub credentials from database (expires: %s)", oauth_manager._token_expires_at)
    return access_token


async def _init_oauth_manager(db_pool: asyncpg.Pool) -> tuple[str, OAuthCredentialManager]:
    """
    Initialize OAuth credential manager and load access token from database.

    Returns:
        Tuple of (access_token, oauth_manager)

    Raises:
        ValueError: If GITHUB_TOKEN_ENCRYPTION_KEY is not set or credentials not in DB
        ConnectionError: If credential loading fails
    """
    encryption_key = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')
    if not encryption_key:
        raise ValueError(
            "GITHUB_TOKEN_ENCRYPTION_KEY not set. "
            "This is required to decrypt stored OAuth credentials."
        )

    try:
        oauth_manager = OAuthCredentialManager(db_pool)
        access_token = await _load_oauth_credentials(oauth_manager)
        return access_token, oauth_manager
    except ValueError:
        raise
    except Exception as e:
        raise ConnectionError(f"Failed to initialize OAuth credentials: {e}")


async def _init_github_client(access_token: str) -> GitHubAPIClient:
    """Initialize GitHub API client."""
    try:
        github_api = GitHubAPIClient(access_token=access_token)
        await github_api.__aenter__()
        return github_api
    except Exception as e:
        raise ConnectionError(f"Failed to initialize GitHub API client: {e}")


async def init_connections():
    """
    Initialize shared GitHub API client and database connection pool.

    When GITHUB_PAT is set, uses it directly and bypasses OAuth credential
    loading from the database. Otherwise, loads OAuth credentials from the DB
    (requires the daily token refresh in trigger/refresh_auth.py to have run).

    Returns:
        Tuple of (GitHubAPIClient, asyncpg.Pool)

    Raises:
        ValueError: If required environment variables are missing
        ConnectionError: If connections cannot be established
    """
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    db_pool = await _init_database_pool(database_url)

    github_pat = os.getenv('GITHUB_PAT')
    if github_pat:
        logger.info("✅ Using GITHUB_PAT for GitHub authentication")
        github_api = await _init_github_client(github_pat)
    else:
        github_access_token, _ = await _init_oauth_manager(db_pool)
        github_api = await _init_github_client(github_access_token)

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
