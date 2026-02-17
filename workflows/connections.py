"""
Shared Resource Management
Handles initialization and cleanup of shared resources like GitHub API client and database pool.
"""

import asyncpg
import asyncio
import os
import logging
from github_api import GitHubAPIClient
from lib.oauth_manager import OAuthCredentialManager

logger = logging.getLogger(__name__)


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
        Tuple of (GitHubAPIClient, asyncpg.Pool, Optional[OAuthCredentialManager])

    Raises:
        ValueError: If required environment variables are missing
        ConnectionError: If connections cannot be established
    """
    # Initialize database connection pool FIRST (needed for OAuth credential manager)
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    db_pool = await _init_database_pool(database_url)

    # Try to use OAuth credential manager if encryption key is set
    oauth_manager = None
    github_access_token = None
    refresh_token = None
    client_id = None
    client_secret = None

    encryption_key = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')
    if encryption_key:
        try:
            logger.info("Attempting to load GitHub credentials from database...")
            oauth_manager = OAuthCredentialManager(db_pool)
            credentials_loaded = await oauth_manager.load_credentials()

            if credentials_loaded:
                # Use credentials from database
                logger.info("✅ Loaded GitHub credentials from database")
                github_access_token = await oauth_manager.get_valid_token()
            else:
                # No credentials in DB - try to seed from env vars
                logger.info("No credentials in database, checking environment variables for initial seed...")
                env_access_token = os.getenv('GITHUB_ACCESS_TOKEN')
                env_refresh_token = os.getenv('GITHUB_REFRESH_TOKEN')

                if env_access_token and env_refresh_token:
                    logger.info("Seeding database with credentials from environment variables...")
                    # Save to DB for future runs
                    await oauth_manager.save_credentials(
                        access_token=env_access_token,
                        refresh_token=env_refresh_token
                    )
                    github_access_token = env_access_token
                    logger.info("✅ Seeded database with initial credentials")
                else:
                    logger.warning("No credentials in DB or environment - OAuth manager will not be used")
                    oauth_manager = None

        except Exception as e:
            logger.warning(f"Failed to initialize OAuth manager: {e}. Falling back to env var tokens.")
            oauth_manager = None

    # Fallback to environment variable tokens if OAuth manager not available
    if not github_access_token:
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
            client_secret=client_secret,
            oauth_manager=oauth_manager
        )
        await github_api.__aenter__()
    except Exception as e:
        raise ConnectionError(f"Failed to initialize GitHub API client: {e}")

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
