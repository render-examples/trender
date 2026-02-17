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
        print(f"✓ GITHUB_TOKEN_ENCRYPTION_KEY already configured")
        return encryption_key

    print("\n🔐 Generating encryption key for secure token storage...")
    encryption_key = Fernet.generate_key().decode('utf-8')

    # Save to .env file
    try:
        set_key(env_path, 'GITHUB_TOKEN_ENCRYPTION_KEY', encryption_key)
        print(f"✅ Encryption key generated and saved to .env")

        # Reload environment to pick up the new key
        load_dotenv(dotenv_path=env_path, override=True)
    except Exception as e:
        print(f"⚠️  Warning: Could not save to .env file: {e}")
        print(f"   Please add this line to your .env file manually:")
        print(f"   GITHUB_TOKEN_ENCRYPTION_KEY={encryption_key}\n")

    return encryption_key


def _verify_token(token: str) -> bool:
    """Verify token by making a test API call."""
    import requests
    
    print("\n🔍 Verifying token...")
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get('https://api.github.com/user', headers=headers)
        if response.status_code == 200:
            username = response.json().get('login', 'Unknown')
            print(f"✅ Token verified! Authenticated as: {username}")
            return True
        
        print(f"⚠️  Warning: Token verification failed (HTTP {response.status_code})")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"⚠️  Warning: Could not verify token: {str(e)}")
    
    return input("Continue anyway? (y/N): ").strip().lower() == 'y'


def setup_pat():
    """Guide user through Personal Access Token (PAT) setup."""
    print("=" * 70)
    print("Personal Access Token (PAT) Setup - Recommended")
    print("=" * 70)
    print("\nThis is the simplest authentication method. You'll create a token")
    print("directly from GitHub settings.\n")
    
    print("📋 Step-by-Step Instructions:\n")
    print("1. Open this URL in your browser:")
    print("   https://github.com/settings/tokens/new\n")
    
    print("2. Fill in the token details:")
    print("   - Note: 'Trender Analytics Access'")
    print("   - Expiration: 'No expiration' (or choose your preference)")
    print("   - Select scopes:")
    print("     ✓ repo (Full control of private repositories)")
    print("     ✓ read:org (Read org and team membership)\n")
    
    print("3. Click 'Generate token' at the bottom of the page\n")
    print("4. Copy the token (starts with 'ghp_' or 'github_pat_')\n")
    print("⚠️  IMPORTANT: Save this token securely - you won't see it again!\n")
    print("=" * 70)
    
    token = input("\nPaste your Personal Access Token here: ").strip()
    
    if not token:
        print("\n❌ Error: No token provided.")
        return None
    
    if not (token.startswith('ghp_') or token.startswith('github_pat_')):
        print("\n⚠️  Warning: Token doesn't match expected format (ghp_* or github_pat_*)")
        if input("Continue anyway? (y/N): ").strip().lower() != 'y':
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
            print(f"\n❌ Error: Port {port} is already in use.")
            print(f"   Run: lsof -ti:{port} | xargs kill -9")
            print("   Then try again.\n")
        else:
            print(f"\n❌ Error: {str(e)}\n")
        return None


async def _save_credentials_to_db(token_data: dict):
    """Save OAuth credentials to database using OAuthCredentialManager."""
    import asyncpg
    from lib.oauth_manager import OAuthCredentialManager

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("\n⚠️  Warning: DATABASE_URL not set, skipping database seeding")
        print("   Credentials will only be available as environment variables")
        return False

    encryption_key = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')
    if not encryption_key:
        print("\n⚠️  Warning: GITHUB_TOKEN_ENCRYPTION_KEY not set, skipping database seeding")
        print("   Generate one with:")
        print('   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
        print("   Then add it to your .env file and Render dashboard")
        return False

    try:
        # Create database connection pool
        print("7. Connecting to database...")
        db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)

        # Save credentials to database
        print("8. Saving credentials to database...")
        oauth_manager = OAuthCredentialManager(db_pool)
        await oauth_manager.save_credentials(
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            expires_in=token_data.get('expires_in', 28800),
            refresh_token_expires_in=token_data.get('refresh_token_expires_in', 15724800)
        )

        await db_pool.close()
        print("✅ Credentials saved to database successfully!")
        return True

    except Exception as e:
        print(f"\n⚠️  Warning: Failed to save credentials to database: {e}")
        print("   Credentials will only be available as environment variables")
        return False


def setup_oauth():
    """Guide user through OAuth App setup."""
    print("=" * 70)
    print("OAuth App Setup - Advanced")
    print("=" * 70)
    print("\nThis method requires creating a GitHub OAuth App and completing")
    print("a browser-based authorization flow.\n")

    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')

    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        print("❌ Error: GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET must be set in .env")
        print("\nTo set up OAuth App:")
        print("1. Go to https://github.com/settings/developers")
        print("2. Click 'New OAuth App'")
        print("3. Set callback URL to: http://localhost:8000/callback")
        print("4. Add GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET to your .env file")
        print("5. Run this script again\n")
        return None

    print("Prerequisites:")
    print(f"  ✓ Client ID: {GITHUB_CLIENT_ID[:10]}...")
    print(f"  ✓ Client Secret: {'*' * 20}")
    print("  ✓ Callback URL: http://localhost:8000/callback\n")

    # Step 1: Start local callback server
    callback_port = 8000
    callback_url = f"http://localhost:{callback_port}/callback"

    print(f"1. Starting local callback server on port {callback_port}...")
    server = _start_oauth_server(callback_port)
    if not server:
        return None

    # Step 2: Create OAuth2Session and generate authorization URL
    scopes = ["repo", "read:org"]
    oauth = OAuth2Session(GITHUB_CLIENT_ID, redirect_uri=callback_url, scope=scopes)
    authorization_url, state = oauth.authorization_url("https://github.com/login/oauth/authorize")

    print("2. Opening browser for authorization...")
    print(f"   If browser doesn't open, visit:\n   {authorization_url}\n")
    webbrowser.open(authorization_url)

    # Step 3: Wait for callback
    print("3. Waiting for authorization callback...")
    print("   (Complete the authorization in your browser)")
    server.handle_request()

    global authorization_code
    if not authorization_code:
        print("\n❌ Error: No authorization code received.")
        return None

    print("4. Authorization code received!")

    # Step 4: Exchange code for access token using OAuth2Session
    print("5. Exchanging code for access token...")
    token_data = get_access_token_from_code(
        GITHUB_CLIENT_ID,
        GITHUB_CLIENT_SECRET,
        authorization_code,
        callback_url
    )

    if not token_data or not token_data.get('access_token'):
        print("\n❌ Error: Failed to get access token.")
        return None

    # Verify the token works
    print("6. Verifying OAuth token...")
    if not _verify_token(token_data['access_token']):
        return None

    # Save credentials to database
    asyncio.run(_save_credentials_to_db(token_data))

    return token_data


def _print_env_instructions(token: str, refresh_token: str, method: str):
    """Print environment variable setup instructions."""
    encryption_key = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')

    print("\n📝 Next Steps:\n")

    if method == 'OAuth' and os.getenv('DATABASE_URL') and encryption_key:
        print("✅ Credentials saved to database! They will automatically refresh.")
        print("\n1. Required environment variables for Render (one-time setup):")
        print(f"   GITHUB_CLIENT_ID={os.getenv('GITHUB_CLIENT_ID')}")
        print(f"   GITHUB_CLIENT_SECRET={os.getenv('GITHUB_CLIENT_SECRET')}")
        print(f"   GITHUB_TOKEN_ENCRYPTION_KEY={encryption_key}")
        print(f"   DATABASE_URL=<your-database-url>")
        print("\n2. Optional (for initial seed on first Render run):")
        print(f"   GITHUB_ACCESS_TOKEN={token}")
        print(f"   GITHUB_REFRESH_TOKEN={refresh_token}")
        print("\n   Note: After first run, tokens auto-refresh from DB. You can remove")
        print("   GITHUB_ACCESS_TOKEN and GITHUB_REFRESH_TOKEN from Render dashboard.")
    else:
        print("1. Environment variables configured in .env:")
        print(f"   ✓ GITHUB_ACCESS_TOKEN={token[:20]}...")

        if encryption_key:
            print(f"   ✓ GITHUB_TOKEN_ENCRYPTION_KEY={encryption_key[:20]}...")

        if refresh_token:
            print(f"   ✓ GITHUB_REFRESH_TOKEN={refresh_token[:20]}...")
            if method == 'OAuth':
                print(f"   ✓ GITHUB_CLIENT_ID={os.getenv('GITHUB_CLIENT_ID')}")
                print(f"   ✓ GITHUB_CLIENT_SECRET={'*' * 20}")

        print("\n2. Add these to your Render Dashboard (trender-wf service > Environment):")
        print(f"   GITHUB_ACCESS_TOKEN={token}")

        if encryption_key:
            print(f"   GITHUB_TOKEN_ENCRYPTION_KEY={encryption_key}")

        if refresh_token:
            print(f"   GITHUB_REFRESH_TOKEN={refresh_token}")
            if method == 'OAuth':
                print(f"   GITHUB_CLIENT_ID={os.getenv('GITHUB_CLIENT_ID')}")
                print(f"   GITHUB_CLIENT_SECRET={os.getenv('GITHUB_CLIENT_SECRET')}")

    print("\n3. Deploy your workflow and trigger a run!")


def _print_security_reminder(method: str):
    """Print security reminders."""
    print("\n⚠️  Security Reminder:")
    print("   - Never commit these tokens to version control")
    print("   - Store them securely (they're like passwords)")
    
    if method == 'PAT':
        print("   - Revoke access at: https://github.com/settings/tokens")
    else:
        print("   - Revoke access at: https://github.com/settings/applications")
        print("   - OAuth tokens auto-refresh when GITHUB_REFRESH_TOKEN is set")


def main():
    """Main authentication setup flow."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         GitHub Authentication Setup for Trender Analytics         ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    # Ensure encryption key exists (required for OAuth credential management)
    print("\n" + "=" * 70)
    print("Encryption Key Setup")
    print("=" * 70)
    encryption_key = _ensure_encryption_key()
    print("=" * 70)

    print("\nChoose your authentication method:\n")
    print("  [1] Personal Access Token (PAT) - Recommended")
    print("      Simple, quick setup. Generate token from GitHub settings.")
    print("      Best for: Individual developers, local development\n")
    
    print("  [2] OAuth App")
    print("      Browser-based authorization flow. Requires OAuth app setup.")
    print("      Best for: Team setups, production deployments\n")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    match choice:
        case '1':
            method = 'PAT'
            result = setup_pat()
            token = result
            refresh_token = None
        case '2':
            method = 'OAuth'
            result = setup_oauth()
            token = result.get('access_token') if result else None
            refresh_token = result.get('refresh_token') if result else None
        case _:
            print("\n❌ Invalid choice. Please run the script again and select 1 or 2.")
            sys.exit(1)
    
    if not token:
        print("\n❌ Setup failed or was cancelled.")
        sys.exit(1)
    
    # Success!
    print("\n" + "=" * 70)
    print(f"✅ SUCCESS! Your GitHub access token ({method}):")
    print("=" * 70)
    print(f"\nAccess Token: {token}\n")
    
    if refresh_token:
        print(f"Refresh Token: {refresh_token}\n")
        print("⚠️  IMPORTANT: OAuth tokens expire after 8 hours!")
        print("   The refresh token allows automatic renewal.\n")
    
    print("=" * 70)
    _print_env_instructions(token, refresh_token, method)
    print("=" * 70)
    _print_security_reminder(method)
    print("=" * 70)


if __name__ == "__main__":
    main()

