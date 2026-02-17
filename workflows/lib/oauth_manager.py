"""
OAuth Credential Manager

Manages GitHub OAuth credentials with encrypted database storage.
Loads credentials from PostgreSQL for use by the GitHub API client.

Token refresh is handled exclusively by trigger/refresh_auth.py, which runs
once daily before workflows start. This class never calls the GitHub OAuth
endpoint - it only reads from and writes to the database.

Security Features:
- Tokens encrypted at rest using Fernet encryption
- No tokens stored in environment variables
"""

import asyncpg
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from lib.encryption import encrypt_token, decrypt_token, get_encryption_key_from_env

logger = logging.getLogger(__name__)


class OAuthCredentialManager:
    """
    Manages GitHub OAuth credentials with encrypted database storage.

    Loads encrypted credentials from PostgreSQL for the GitHub API client.
    Does not refresh tokens - that is handled exclusively by refresh_auth.py.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize OAuth credential manager.

        Args:
            db_pool: PostgreSQL connection pool for credential storage
        """
        self.db_pool = db_pool
        self.encryption_key = get_encryption_key_from_env()

        # Cached credentials (decrypted in memory)
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._refresh_token_expires_at: Optional[datetime] = None

        if not self.encryption_key:
            raise ValueError(
                "GITHUB_TOKEN_ENCRYPTION_KEY not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

    async def load_credentials(self) -> bool:
        """
        Load and decrypt credentials from database.

        Returns:
            True if credentials were loaded successfully, False if no credentials exist

        Raises:
            ValueError: If credentials exist but cannot be decrypted
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT access_token_encrypted, token_expires_at "
                    "FROM github_oauth_credentials WHERE id = 1"
                )

            if not row:
                logger.info("No credentials found in database")
                return False

            self._access_token = decrypt_token(row['access_token_encrypted'], self.encryption_key)
            self._token_expires_at = row['token_expires_at']

            logger.info(f"Credentials loaded. Access token expires at: {self._token_expires_at}")
            return True

        except Exception as e:
            logger.error(f"Failed to load credentials from database: {e}")
            raise ValueError(f"Failed to load credentials: {e}")

    async def save_credentials(self, access_token: str, refresh_token: str,
                               expires_in: int = 28800, refresh_token_expires_in: int = 15724800) -> None:
        """
        Encrypt and save credentials to database.

        Args:
            access_token: GitHub OAuth access token
            refresh_token: GitHub OAuth refresh token
            expires_in: Access token lifetime in seconds (default: 8 hours)
            refresh_token_expires_in: Refresh token lifetime in seconds (default: 6 months)
        """
        try:
            now = datetime.now(timezone.utc)
            token_expires_at = now + timedelta(seconds=expires_in)
            refresh_token_expires_at = now + timedelta(seconds=refresh_token_expires_in)

            access_token_encrypted = encrypt_token(access_token, self.encryption_key)
            refresh_token_encrypted = encrypt_token(refresh_token, self.encryption_key)

            async with self.db_pool.acquire() as conn:
                await conn.execute(
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

            self._access_token = access_token
            self._refresh_token = refresh_token
            self._token_expires_at = token_expires_at
            self._refresh_token_expires_at = refresh_token_expires_at

            logger.info(f"Credentials saved to database. Expires at: {token_expires_at}")

        except Exception as e:
            logger.error(f"Failed to save credentials to database: {e}")
            raise ValueError(f"Failed to save credentials: {e}")

    async def get_valid_token(self) -> str:
        """
        Load and return the current access token from the database.

        Token refresh is not performed here - it is handled exclusively by
        trigger/refresh_auth.py before the workflow runs each day.

        Returns:
            GitHub OAuth access token loaded from database

        Raises:
            ValueError: If no credentials exist in the database
        """
        if not self._access_token:
            credentials_loaded = await self.load_credentials()
            if not credentials_loaded:
                raise ValueError(
                    "No GitHub credentials found in database. "
                    "Run 'python trigger/refresh_auth.py' or 'python workflows/auth_setup.py' "
                    "to set up OAuth credentials."
                )

        logger.info(f"[AUTH] Using access token (expires: {self._token_expires_at})")
        return self._access_token
