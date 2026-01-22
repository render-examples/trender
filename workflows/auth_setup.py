"""
GitHub Authentication Setup
Supports two authentication methods:
1. Personal Access Token (PAT) - Recommended for simplicity
2. OAuth App - For advanced use cases requiring user authorization flow
"""

import os
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


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
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            return None
    
    # Verify token works by making a simple API call
    print("\n🔍 Verifying token...")
    import requests
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get('https://api.github.com/user', headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            username = user_data.get('login', 'Unknown')
            print(f"✅ Token verified! Authenticated as: {username}")
        else:
            print(f"⚠️  Warning: Token verification failed (HTTP {response.status_code})")
            print(f"   Response: {response.text}")
            confirm = input("Continue anyway? (y/N): ").strip().lower()
            if confirm != 'y':
                return None
    except Exception as e:
        print(f"⚠️  Warning: Could not verify token: {str(e)}")
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            return None
    
    return token


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


def get_access_token_from_code(client_id, client_secret, code):
    """Exchange authorization code for access token."""
    import requests
    
    url = "https://github.com/login/oauth/access_token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code
    }
    headers = {'Accept': 'application/json'}
    
    response = requests.post(url, data=data, headers=headers)
    result = response.json()
    return result.get('access_token')


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
    print(f"  ✓ Callback URL: http://localhost:8000/callback\n")
    
    # Step 1: Start local callback server
    callback_port = 8000
    callback_url = f"http://localhost:{callback_port}/callback"
    
    print(f"1. Starting local callback server on port {callback_port}...")
    try:
        server = HTTPServer(('localhost', callback_port), OAuthCallbackHandler)
    except OSError as e:
        if 'Address already in use' in str(e):
            print(f"\n❌ Error: Port {callback_port} is already in use.")
            print(f"   Run: lsof -ti:{callback_port} | xargs kill -9")
            print(f"   Then try again.\n")
        else:
            print(f"\n❌ Error: {str(e)}\n")
        return None
    
    # Step 2: Open browser for authorization
    scopes = "repo,read:org"
    auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={callback_url}"
        f"&scope={scopes}"
    )
    
    print(f"2. Opening browser for authorization...")
    print(f"   If browser doesn't open, visit:\n   {auth_url}\n")
    webbrowser.open(auth_url)
    
    # Step 3: Wait for callback
    print("3. Waiting for authorization callback...")
    print("   (Complete the authorization in your browser)")
    server.handle_request()
    
    global authorization_code
    if not authorization_code:
        print("\n❌ Error: No authorization code received.")
        return None
    
    print("4. Authorization code received!")
    
    # Step 4: Exchange code for access token
    print("5. Exchanging code for access token...")
    access_token = get_access_token_from_code(
        GITHUB_CLIENT_ID,
        GITHUB_CLIENT_SECRET,
        authorization_code
    )
    
    if not access_token:
        print("\n❌ Error: Failed to get access token.")
        return None
    
    return access_token


def main():
    """Main authentication setup flow."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         GitHub Authentication Setup for Trender Analytics         ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print("\nChoose your authentication method:\n")
    print("  [1] Personal Access Token (PAT) - Recommended")
    print("      Simple, quick setup. Generate token from GitHub settings.")
    print("      Best for: Individual developers, local development\n")
    
    print("  [2] OAuth App")
    print("      Browser-based authorization flow. Requires OAuth app setup.")
    print("      Best for: Team setups, production deployments\n")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    token = None
    method = None
    
    if choice == '1':
        method = 'PAT'
        token = setup_pat()
    elif choice == '2':
        method = 'OAuth'
        token = setup_oauth()
    else:
        print("\n❌ Invalid choice. Please run the script again and select 1 or 2.")
        sys.exit(1)
    
    if not token:
        print("\n❌ Setup failed or was cancelled.")
        sys.exit(1)
    
    # Success!
    print("\n" + "=" * 70)
    print(f"✅ SUCCESS! Your GitHub access token ({method}):")
    print("=" * 70)
    print(f"\n{token}\n")
    print("=" * 70)
    print("\n📝 Next Steps:\n")
    print("1. Add this to your .env file:")
    print(f"   GITHUB_ACCESS_TOKEN={token}\n")
    print("2. Add the same token to your Render Dashboard:")
    print("   - Go to your workflow service (trender-wf)")
    print("   - Navigate to Environment tab")
    print("   - Add: GITHUB_ACCESS_TOKEN={token}\n")
    print("3. Deploy your workflow and trigger a run!")
    print("=" * 70)
    print("\n⚠️  Security Reminder:")
    print("   - Never commit this token to version control")
    print("   - Store it securely (it's like a password)")
    print("   - Revoke access at: https://github.com/settings/tokens")
    print("=" * 70)


if __name__ == "__main__":
    main()

