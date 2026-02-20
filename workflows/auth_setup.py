"""
GitHub Authentication Setup
Supports two authentication methods:
1. Personal Access Token (PAT) - Recommended for simplicity
2. OAuth App - For advanced use cases requiring user authorization flow
"""

import os
import sys
import asyncio
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
from dotenv import load_dotenv, set_key
from requests_oauthlib import OAuth2Session
from cryptography.fernet import Fernet

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)


def _ensure_encryption_key() -> str:
    """Ensure GITHUB_TOKEN_ENCRYPTION_KEY exists, generate if missing."""
    encryption_key = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')

    if encryption_key:
        return encryption_key

    print("Generating encryption key...")
    encryption_key = Fernet.generate_key().decode('utf-8')

    # Save to .env file
    try:
        set_key(env_path, 'GITHUB_TOKEN_ENCRYPTION_KEY', encryption_key)
        print("✓ Encryption key saved to .env")
        load_dotenv(dotenv_path=env_path, override=True)
    except Exception as e:
        print(f"⚠ Could not save to .env: {e}")
        print(f"Add manually: GITHUB_TOKEN_ENCRYPTION_KEY={encryption_key}\n")

    return encryption_key


def _verify_token(token: str) -> bool:
    """Verify token by making a test API call."""
    import requests

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    try:
        response = requests.get('https://api.github.com/user', headers=headers)
        if response.status_code == 200:
            username = response.json().get('login', 'Unknown')
            print(f"✓ Authenticated as {username}")
            return True

        print(f"⚠ Token verification failed (HTTP {response.status_code})")
    except Exception as e:
        print(f"⚠ Could not verify token: {str(e)}")

    return input("Continue anyway? (y/N): ").strip().lower() == 'y'


def setup_pat():
    """Guide user through Personal Access Token (PAT) setup."""
    print("\n→ Personal Access Token Setup (Recommended)")
    print("\n1. Open: https://github.com/settings/tokens/new")
    print("2. Set scopes: repo, read:org")
    print("3. Copy token (starts with ghp_ or github_pat_)\n")

    token = input("Paste token: ").strip()

    if not token:
        print("✗ No token provided")
        return None

    if not (token.startswith('ghp_') or token.startswith('github_pat_')):
        print("⚠ Token format unexpected")
        if input("Continue? (y/N): ").strip().lower() != 'y':
            return None

    return token if _verify_token(token) else None


# OAuth callback handler (from original oauth_setup.py)
authorization_code = None

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global authorization_code
        
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        if 'code' in params:
            authorization_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("""
                <html>
                <body style="font-family: system-ui; padding: 40px; text-align: center;">
                    <h1 style="color: #2da44e;">✓ Authorization Successful!</h1>
                    <p>You can close this window and return to your terminal.</p>
                </body>
                </html>
            """.encode('utf-8'))
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("""
                <html>
                <body style="font-family: system-ui; padding: 40px; text-align: center;">
                    <h1 style="color: #d1242f;">✗ Authorization Failed</h1>
                    <p>No authorization code received.</p>
                </body>
                </html>
            """.encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # Suppress server logs


def get_access_token_from_code(client_id, client_secret, code, redirect_uri):
    """Exchange authorization code for access token and refresh token using OAuth2Session."""
    # Create OAuth2Session for token exchange
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri)

    token_url = "https://github.com/login/oauth/access_token"

    # Fetch the token
    token = oauth.fetch_token(
        token_url,
        client_secret=client_secret,
        code=code,
        include_client_id=True
    )

    # Return the full OAuth response including refresh token
    return {
        'access_token': token.get('access_token'),
        'refresh_token': token.get('refresh_token'),
        'expires_in': token.get('expires_in', 28800),  # Default 8 hours
        'refresh_token_expires_in': token.get('refresh_token_expires_in', 15724800),  # Default 6 months
        'token_type': token.get('token_type', 'bearer')
    }


def _start_oauth_server(port: int) -> HTTPServer:
    """Start local OAuth callback server."""
    try:
        return HTTPServer(('localhost', port), OAuthCallbackHandler)
    except OSError as e:
        if 'Address already in use' in str(e):
            print(f"\n✗ Error: Port {port} is already in use")
            print(f"  Run: lsof -ti:{port} | xargs kill -9")
            print("  Then try again\n")
        else:
            print(f"\n✗ Error: {str(e)}\n")
        return None


async def _save_credentials_to_db(token_data: dict):
    """Save OAuth credentials to database using OAuthCredentialManager."""
    import asyncpg
    from lib.oauth_manager import OAuthCredentialManager

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("⚠ DATABASE_URL not set, skipping database storage")
        return False

    encryption_key = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')
    if not encryption_key:
        print("⚠ GITHUB_TOKEN_ENCRYPTION_KEY not set, skipping database storage")
        return False

    try:
        print("Saving credentials to database...")
        db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)

        oauth_manager = OAuthCredentialManager(db_pool)
        await oauth_manager.save_credentials(
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            expires_in=token_data.get('expires_in', 28800),
            refresh_token_expires_in=token_data.get('refresh_token_expires_in', 15724800)
        )

        await db_pool.close()
        print("✓ Credentials saved to database")
        return True

    except Exception as e:
        print(f"⚠ Failed to save to database: {e}")
        return False


def setup_oauth():
    """Guide user through OAuth App setup."""
    print("\n→ OAuth App Setup (Advanced)")

    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')

    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        print("✗ GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET required in .env")
        print("\n1. Go to https://github.com/settings/developers")
        print("2. Create OAuth App with callback: http://localhost:8000/callback")
        print("3. Add credentials to .env\n")
        return None

    # Start local callback server
    callback_port = 8000
    callback_url = f"http://localhost:{callback_port}/callback"

    print(f"Starting callback server on port {callback_port}...")
    server = _start_oauth_server(callback_port)
    if not server:
        return None

    # Create OAuth2Session and generate authorization URL
    scopes = ["repo", "read:org"]
    oauth = OAuth2Session(GITHUB_CLIENT_ID, redirect_uri=callback_url, scope=scopes)
    authorization_url, state = oauth.authorization_url("https://github.com/login/oauth/authorize")

    print("Opening browser for authorization...")
    webbrowser.open(authorization_url)
    print("Waiting for authorization...")
    server.handle_request()

    global authorization_code
    if not authorization_code:
        print("✗ No authorization code received")
        return None

    # Exchange code for access token
    token_data = get_access_token_from_code(
        GITHUB_CLIENT_ID,
        GITHUB_CLIENT_SECRET,
        authorization_code,
        callback_url
    )

    if not token_data or not token_data.get('access_token'):
        print("✗ Failed to get access token")
        return None

    # Verify the token works
    if not _verify_token(token_data['access_token']):
        return None

    # Save credentials to database
    asyncio.run(_save_credentials_to_db(token_data))

    return token_data


def _print_oauth_db_instructions(token: str, refresh_token: str, encryption_key: str):
    """Print instructions for OAuth with database setup."""
    print("\n→ Render Environment Variables (copy these):")
    print(f"GITHUB_CLIENT_ID={os.getenv('GITHUB_CLIENT_ID')}")
    print(f"GITHUB_CLIENT_SECRET={os.getenv('GITHUB_CLIENT_SECRET')}")
    print(f"GITHUB_TOKEN_ENCRYPTION_KEY={encryption_key}")
    print(f"DATABASE_URL=<your-database-url>")
    print(f"\nOptional initial seed:")
    print(f"GITHUB_ACCESS_TOKEN={token}")
    print(f"GITHUB_REFRESH_TOKEN={refresh_token}")


def _print_manual_setup_instructions(token: str, refresh_token: str, method: str, encryption_key: str):
    """Print instructions for manual environment setup."""
    print("\n→ Render Environment Variables (copy these):")
    print(f"GITHUB_ACCESS_TOKEN={token}")
    if encryption_key:
        print(f"GITHUB_TOKEN_ENCRYPTION_KEY={encryption_key}")
    if refresh_token:
        print(f"GITHUB_REFRESH_TOKEN={refresh_token}")
        if method == 'OAuth':
            print(f"GITHUB_CLIENT_ID={os.getenv('GITHUB_CLIENT_ID')}")
            print(f"GITHUB_CLIENT_SECRET={os.getenv('GITHUB_CLIENT_SECRET')}")


def _print_env_instructions(token: str, refresh_token: str, method: str):
    """Print environment variable setup instructions."""
    encryption_key = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')

    if method == 'OAuth' and os.getenv('DATABASE_URL') and encryption_key:
        _print_oauth_db_instructions(token, refresh_token, encryption_key)
    else:
        _print_manual_setup_instructions(token, refresh_token, method, encryption_key)


def _print_security_reminder(method: str):
    """Print security reminders."""
    print("\n⚠ Security: Never commit tokens to git")
    if method == 'PAT':
        print("Revoke at: https://github.com/settings/tokens")
    else:
        print("Revoke at: https://github.com/settings/applications")


def main():
    """Main authentication setup flow."""
    print("\n→ GitHub Authentication Setup")

    print("\nChoose authentication method:")
    print("[1] Personal Access Token (PAT) - Recommended")
    print("[2] OAuth App - Advanced\n")

    choice = input("Choice (1 or 2): ").strip()

    match choice:
        case '1':
            result = setup_pat()
            if not result:
                print("✗ Setup failed")
                sys.exit(1)
            print(f"\n✅ PAT Setup Complete")
            print(f"\nAdd to Render environment (trender-wf and trender-cron):")
            print(f"  GITHUB_PAT={result}")
            print(f"\n⚠ Never commit this token to git. Revoke at: https://github.com/settings/tokens")
        case '2':
            encryption_key = _ensure_encryption_key()
            result = setup_oauth()
            if not result or not result.get('access_token'):
                print("✗ Setup failed")
                sys.exit(1)
            print(f"\n✅ OAuth Setup Complete")
            print(f"\nAdd to Render environment (trender-wf and trender-cron):")
            print(f"  GITHUB_CLIENT_ID={os.getenv('GITHUB_CLIENT_ID')}")
            print(f"  GITHUB_CLIENT_SECRET={os.getenv('GITHUB_CLIENT_SECRET')}")
            print(f"  GITHUB_TOKEN_ENCRYPTION_KEY={encryption_key}")
            print(f"\n⚠ Never commit these to git. Revoke at: https://github.com/settings/applications")
        case _:
            print("✗ Invalid choice")
            sys.exit(1)

    print()


if __name__ == "__main__":
    main()

