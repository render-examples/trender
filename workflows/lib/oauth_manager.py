"""
OAuth Credential Manager

Manages GitHub OAuth credentials with automatic refresh, encrypted database storage,
and proactive expiration handling.

This module handles the complete lifecycle of GitHub OAuth tokens:
1. Loading encrypted tokens from PostgreSQL
2. Automatic refresh when tokens expire or are about to expire
3. Secure storage of refreshed tokens back to database
4. Integration with GitHub API client for seamless authentication

Security Features:
- Tokens encrypted at rest using Fernet encryption
- Proactive refresh (before 5-minute expiry window)
- Reactive refresh (on 401 Unauthorized errors)
- Automatic token lifecycle management
- No tokens stored in environment variables (only CLIENT_ID/SECRET)

Usage:
    async with OAuthCredentialManager(db_pool) as manager:
        token = await manager.get_valid_token()
        # Use token for GitHub API calls
"""

import asyncpg
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
import aiohttp
from oauthlib.oauth2 import WebApplicationClient

from lib.encryption import encrypt_token, decrypt_token, get_encryption_key_from_env

logger = logging.getLogger(__name__)


class OAuthCredentialManager:
    """
    Manages GitHub OAuth credentials with automatic refresh and encrypted storage.
    
    This class handles:
    - Loading encrypted credentials from PostgreSQL
    - Automatic token refresh using CLIENT_ID/SECRET
    - Proactive expiration checks (refresh before expiry)
    - Reactive refresh on 401 errors
    - Secure storage back to database
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize OAuth credential manager.

        Args:
            db_pool: PostgreSQL connection pool for credential storage
        """
        self.db_pool = db_pool
        self.client_id = os.getenv('GITHUB_CLIENT_ID')
        self.client_secret = os.getenv('GITHUB_CLIENT_SECRET')
        self.encryption_key = get_encryption_key_from_env()

        # OAuth2 client for token management
        self.oauth_client = WebApplicationClient(client_id=self.client_id)

        # Cached credentials (decrypted in memory)
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._refresh_token_expires_at: Optional[datetime] = None

        # Validate configuration
        if not self.encryption_key:
            raise ValueError(
                "GITHUB_TOKEN_ENCRYPTION_KEY not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET must be set for OAuth token refresh"
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
                    """
                    SELECT access_token_encrypted, refresh_token_encrypted,
                           token_expires_at, refresh_token_expires_at
                    FROM github_oauth_credentials
                    WHERE id = 1
                    """
                )
            
            if not row:
                logger.info("No credentials found in database")
                return False
            
            # Decrypt tokens
            self._access_token = decrypt_token(row['access_token_encrypted'], self.encryption_key)
            self._refresh_token = decrypt_token(row['refresh_token_encrypted'], self.encryption_key)
            self._token_expires_at = row['token_expires_at']
            self._refresh_token_expires_at = row['refresh_token_expires_at']
            
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
            
        Raises:
            ValueError: If encryption or database save fails
        """
        try:
            # Calculate expiration times
            now = datetime.now(timezone.utc)
            token_expires_at = now + timedelta(seconds=expires_in)
            refresh_token_expires_at = now + timedelta(seconds=refresh_token_expires_in)
            
            # Encrypt tokens
            access_token_encrypted = encrypt_token(access_token, self.encryption_key)
            refresh_token_encrypted = encrypt_token(refresh_token, self.encryption_key)
            
            # Save to database (upsert)
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
                        refresh_token_expires_at = EXCLUDED.refresh_token_expires_at
                    """,
                    access_token_encrypted, refresh_token_encrypted,
                    token_expires_at, refresh_token_expires_at
                )
            
            # Update in-memory cache
            self._access_token = access_token
            self._refresh_token = refresh_token
            self._token_expires_at = token_expires_at
            self._refresh_token_expires_at = refresh_token_expires_at
            
            logger.info(f"Credentials saved to database. Expires at: {token_expires_at}")
            
        except Exception as e:
            logger.error(f"Failed to save credentials to database: {e}")
            raise ValueError(f"Failed to save credentials: {e}")
    
    def is_token_expiring_soon(self, minutes: int = 5) -> bool:
        """
        Check if access token will expire within specified minutes.
        
        Args:
            minutes: Warning window in minutes (default: 5)
            
        Returns:
            True if token expires within the warning window
        """
        if not self._token_expires_at:
            return True
        
        now = datetime.now(timezone.utc)
        time_until_expiry = self._token_expires_at - now
        return time_until_expiry.total_seconds() < (minutes * 60)
    
    async def _exchange_refresh_token(self) -> dict:
        """
        Make HTTP request to exchange refresh token for new access token using oauthlib.

        Returns:
            Response dictionary with new tokens

        Raises:
            ValueError: If refresh fails or response is invalid
        """
        token_url = "https://github.com/login/oauth/access_token"

        # Use oauthlib to prepare the refresh token request
        uri, headers, body = self.oauth_client.prepare_refresh_token_request(
            token_url=token_url,
            refresh_token=self._refresh_token,
            client_id=self.client_id,
            client_secret=self.client_secret
        )

        # Make the request with aiohttp
        # Use TCPConnector with force_close to ensure proper cleanup
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(uri, headers=headers, data=body) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"Token refresh failed (HTTP {response.status}): {error_text}")

                response_text = await response.text()

                # Use oauthlib to parse the response
                token_response = self.oauth_client.parse_request_body_response(response_text)

                if not token_response.get('access_token'):
                    raise ValueError(f"Token refresh failed: no access_token in response: {token_response}")

                return token_response
    
    async def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Exchanges the refresh token for a new access token using GitHub's OAuth API.
        Automatically updates the database with new credentials.
        
        Returns:
            True if refresh was successful, False otherwise
            
        Raises:
            ValueError: If refresh token is missing or CLIENT_ID/SECRET not configured
        """
        if not self._refresh_token:
            raise ValueError("Cannot refresh token: no refresh token available")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Cannot refresh token: GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET must be set")
        
        logger.info("Refreshing OAuth access token...")
        
        try:
            result = await self._exchange_refresh_token()

            # GitHub may return a new refresh token
            new_access_token = result['access_token']
            new_refresh_token = result.get('refresh_token', self._refresh_token)
            expires_in = int(result.get('expires_in', 28800))  # Default 8 hours
            refresh_token_expires_in = int(result.get('refresh_token_expires_in', 15724800))  # Default 6 months

            # Save new tokens to database
            await self.save_credentials(
                new_access_token,
                new_refresh_token,
                expires_in,
                refresh_token_expires_in
            )
            
            logger.info(f"✅ OAuth token refreshed successfully! Expires: {self._token_expires_at}")
            return True
            
        except Exception as e:
            logger.error(f"Token refresh failed with exception: {e}")
            return False
    
    async def get_valid_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        This method implements both proactive and reactive refresh:
        1. Proactive: Refreshes if token expires within 5 minutes
        2. Ensures token is always valid before returning
        
        Returns:
            Valid GitHub OAuth access token
            
        Raises:
            ValueError: If no credentials exist or refresh fails
        """
        # Load credentials if not already loaded
        if not self._access_token:
            credentials_loaded = await self.load_credentials()
            if not credentials_loaded:
                raise ValueError(
                    "No GitHub credentials found in database. "
                    "Run 'python workflows/auth_setup.py' to set up OAuth credentials."
                )
        
        # Proactive refresh if expiring soon
        if self.is_token_expiring_soon(minutes=5):
            logger.info(f"Token expires soon ({self._token_expires_at}), refreshing proactively...")
            refresh_success = await self.refresh_access_token()
            if not refresh_success:
                raise ValueError("Failed to refresh expiring token")
        
        return self._access_token
    
    async def handle_401_error(self) -> bool:
        """
        Handle 401 Unauthorized error by attempting token refresh.
        
        This is the reactive refresh mechanism called when GitHub API
        returns 401 (token expired or invalid).
        
        Returns:
            True if token was successfully refreshed, False otherwise
        """
        logger.warning("Received 401 Unauthorized - attempting reactive token refresh...")
        return await self.refresh_access_token()

