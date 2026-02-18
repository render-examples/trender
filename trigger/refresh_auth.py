"""
GitHub OAuth Token Refresh

Refreshes GitHub OAuth access token using the stored refresh token.
This is the ONLY place where auth credentials are refreshed.

Credentials are stored in the database only - never in environment variables.
Must be run once daily, directly before the workflows run.

GitHub refresh tokens are single-use: each refresh issues a new refresh token
and invalidates the previous one. Running this script multiple times or from
multiple places simultaneously would break authentication.
"""

import asyncio
import asyncpg
import aiohttp
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Load .env file from parent directory (override=True ensures .env always wins)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_fernet(encryption_key_str: str) -> Fernet:
    return Fernet(encryption_key_str.encode('utf-8'))


def _encrypt(fernet: Fernet, value: str) -> str:
    return fernet.encrypt(value.encode('utf-8')).decode('utf-8')


def _decrypt(fernet: Fernet, encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode('utf-8')).decode('utf-8')


async def refresh_github_auth() -> bool:
    """
    Refresh GitHub OAuth credentials and store in database.

    Loads the current refresh token from the database, exchanges it for
    new credentials from GitHub, and saves the new credentials back to DB.

    GitHub refresh tokens are single-use: each call to this function
    consumes the current refresh token and receives a new one.

    Returns:
        True if refresh succeeded, False otherwise
    """
    database_url = os.getenv('DATABASE_URL')
    client_id = os.getenv('GITHUB_CLIENT_ID')
    client_secret = os.getenv('GITHUB_CLIENT_SECRET')
    encryption_key_str = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')

    missing = [k for k, v in {
        'DATABASE_URL': database_url,
        'GITHUB_CLIENT_ID': client_id,
        'GITHUB_CLIENT_SECRET': client_secret,
        'GITHUB_TOKEN_ENCRYPTION_KEY': encryption_key_str,
    }.items() if not v]

    if missing:
        logger.error(f"[AUTH] Missing required environment variables: {', '.join(missing)}")
        return False

    fernet = _get_fernet(encryption_key_str)
    pool = None

    try:
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2, timeout=30)

        # Load current credentials from database
        row = await pool.fetchrow(
            "SELECT refresh_token_encrypted, token_expires_at FROM github_oauth_credentials WHERE id = 1"
        )

        if not row:
            logger.error("[AUTH] No credentials found in database. Run auth_setup.py first.")
            return False

        refresh_token = _decrypt(fernet, row['refresh_token_encrypted'])
        logger.info(
            f"[AUTH] Using refresh token at {datetime.now(timezone.utc).isoformat()} "
            f"(current access token expires: {row['token_expires_at']})"
        )

        # Exchange refresh token for new access token.
        # GitHub refresh tokens are single-use - this consumes the current one.
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[AUTH] GitHub token refresh HTTP {response.status}: {error_text}")
                    return False

                result = await response.json()

        if "error" in result:
            logger.error(
                f"[AUTH] GitHub token refresh failed: {result.get('error')} - "
                f"{result.get('error_description', '')}"
            )
            return False

        new_access_token = result.get('access_token')
        new_refresh_token = result.get('refresh_token', refresh_token)
        expires_in = int(result.get('expires_in', 28800))
        refresh_token_expires_in = int(result.get('refresh_token_expires_in', 15724800))

        if not new_access_token:
            logger.error(f"[AUTH] No access_token in GitHub response: {result}")
            return False

        # Encrypt and save new credentials
        now = datetime.now(timezone.utc)
        token_expires_at = now + timedelta(seconds=expires_in)
        refresh_token_expires_at = now + timedelta(seconds=refresh_token_expires_in)

        access_token_encrypted = _encrypt(fernet, new_access_token)
        refresh_token_encrypted = _encrypt(fernet, new_refresh_token)

        await pool.execute(
            """
            INSERT INTO github_oauth_credentials
                (id, access_token_encrypted, refresh_token_encrypted,
                 token_expires_at, refresh_token_expires_at)
            VALUES (1, $1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET
                access_token_encrypted = EXCLUDED.access_token_encrypted,
                refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                token_expires_at = EXCLUDED.token_expires_at,
                refresh_token_expires_at = EXCLUDED.refresh_token_expires_at,
                updated_at = NOW()
            """,
            access_token_encrypted, refresh_token_encrypted,
            token_expires_at, refresh_token_expires_at
        )

        refresh_changed = new_refresh_token != refresh_token
        logger.info(f"[AUTH] Token refreshed successfully (expires: {token_expires_at.isoformat()})")
        if refresh_changed:
            logger.info("[AUTH] New refresh token issued")

        return True

    except Exception as e:
        logger.error(f"[AUTH] Unexpected error during token refresh: {e}")
        return False

    finally:
        if pool:
            await pool.close()


if __name__ == "__main__":
    success = asyncio.run(refresh_github_auth())
    if not success:
        sys.exit(1)
