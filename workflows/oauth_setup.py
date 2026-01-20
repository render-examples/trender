"""
One-time OAuth Setup Script
Run this locally to authorize your GitHub OAuth App and get an access token.
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

GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')

if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
    print("Error: GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET must be set in .env")
    sys.exit(1)

# OAuth callback handler
authorization_code = None

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global authorization_code
        
        # Parse the callback URL
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        if 'code' in params:
            authorization_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body>
                    <h1>Authorization Successful!</h1>
                    <p>You can close this window and return to your terminal.</p>
                </body>
                </html>
            """)
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body>
                    <h1>Authorization Failed</h1>
                    <p>No authorization code received.</p>
                </body>
                </html>
            """)
    
    def log_message(self, format, *args):
        pass  # Suppress server logs


def get_access_token():
    """Complete the OAuth flow and get an access token."""
    import aiohttp
    import asyncio
    
    async def exchange_code_for_token(code):
        async with aiohttp.ClientSession() as session:
            url = "https://github.com/login/oauth/access_token"
            data = {
                'client_id': GITHUB_CLIENT_ID,
                'client_secret': GITHUB_CLIENT_SECRET,
                'code': code
            }
            headers = {'Accept': 'application/json'}
            
            async with session.post(url, data=data, headers=headers) as response:
                result = await response.json()
                return result.get('access_token')
    
    return asyncio.run(exchange_code_for_token(authorization_code))


def main():
    print("=== GitHub OAuth App Setup ===\n")
    print("This script will open your browser to authorize the GitHub OAuth App.")
    print("After authorization, you'll be redirected back and the token will be displayed.\n")
    
    # Step 1: Start local callback server
    callback_port = 8000
    callback_url = f"http://localhost:{callback_port}/callback"
    
    print(f"1. Starting local callback server on port {callback_port}...")
    server = HTTPServer(('localhost', callback_port), OAuthCallbackHandler)
    
    # Step 2: Open browser for authorization
    scopes = "repo,read:org"  # Adjust scopes as needed
    auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={callback_url}"
        f"&scope={scopes}"
    )
    
    print(f"2. Opening browser for authorization...")
    print(f"   If the browser doesn't open, visit: {auth_url}\n")
    webbrowser.open(auth_url)
    
    # Step 3: Wait for callback
    print("3. Waiting for authorization callback...")
    server.handle_request()  # Handle one request (the callback)
    
    if not authorization_code:
        print("\nError: No authorization code received.")
        sys.exit(1)
    
    print("4. Authorization code received!")
    
    # Step 4: Exchange code for access token
    print("5. Exchanging code for access token...")
    access_token = get_access_token()
    
    if not access_token:
        print("\nError: Failed to get access token.")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✓ SUCCESS! Your GitHub OAuth access token:")
    print("="*60)
    print(f"\n{access_token}\n")
    print("="*60)
    print("\nAdd this to your .env file and Render Dashboard:")
    print(f"GITHUB_ACCESS_TOKEN={access_token}")
    print("\nAnd update your render.yaml to use GITHUB_ACCESS_TOKEN instead of")
    print("GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET")
    print("="*60)


if __name__ == "__main__":
    main()

