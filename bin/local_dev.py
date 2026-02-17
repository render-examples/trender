#!/usr/bin/env python3
"""
Local Development Orchestrator for Trender Workflows

This script automates local workflow testing by:
1. Starting a local task server in a background process
2. Waiting for it to be ready
3. Triggering the workflow against the local server
4. Streaming logs from both processes
5. Graceful cleanup on exit (Ctrl+C)

Usage:
    python bin/local_dev.py                    # Run with full logs
    python bin/local_dev.py --trigger-only     # Only trigger (assumes server is running)
    python bin/local_dev.py --server-only      # Only start server
    python bin/local_dev.py --port 8121        # Use custom port

Environment:
    Reads configuration from .env file in project root
    Key variables: DATABASE_URL, GITHUB_ACCESS_TOKEN, RENDER_API_KEY, etc.
"""

import os
import sys
import subprocess
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests

# Get project root (parent of bin/)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / '.env'

# Load environment variables from .env (override=True ensures .env always wins
# over any stale values already exported in the shell environment)
load_dotenv(dotenv_path=ENV_PATH, override=True)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'


def print_message(message: str, msg_type: str = 'info', prefix: str = '') -> None:
    """Print a colored message with optional prefix."""
    colors = {
        'success': Colors.GREEN,
        'error': Colors.RED,
        'warning': Colors.YELLOW,
        'info': Colors.BLUE,
        'header': Colors.BLUE
    }
    color = colors.get(msg_type, '')
    output = sys.stderr if msg_type == 'error' else sys.stdout
    full_message = f"{prefix}{message}" if prefix else message
    print(f"{color}{full_message}{Colors.ENDC}", file=output)


def print_header(message: str):
    """Print a colored header message"""
    print_message(f"\n{'='*80}\n{message}\n{'='*80}\n", 'header')


def print_success(message: str):
    """Print a success message"""
    print_message(f"✓ {message}", 'success')


def print_error(message: str):
    """Print an error message"""
    print_message(f"✗ {message}", 'error')


def print_info(message: str):
    """Print an info message"""
    print_message(f"ℹ {message}", 'info')


def print_warning(message: str):
    """Print a warning message"""
    print_message(f"⚠ {message}", 'warning')


def _is_placeholder_value(var_name: str, value: str) -> bool:
    """Check if an environment variable value is a placeholder."""
    if not value:
        return True

    placeholder_patterns = {
        'DATABASE_URL': ['postgresql://username:password@host', 'postgresql://user:pass@localhost'],
        'GITHUB_ACCESS_TOKEN': ['ghp_your_access_token_here', 'github_pat_your'],
        'RENDER_API_KEY': ['rnd_your_render_api_key_here'],
        'RENDER_WORKFLOW_SLUG': ['your_workflow_slug_here', 'trender-wf-example'],
    }

    patterns = placeholder_patterns.get(var_name, [])
    for pattern in patterns:
        if value.startswith(pattern) or value == pattern:
            return True

    return False


def validate_environment():
    """Validate required environment variables"""
    print_header("Validating Environment")

    required_vars = {
        'DATABASE_URL': 'PostgreSQL connection string',
        'GITHUB_ACCESS_TOKEN': 'GitHub API access token',
        'RENDER_API_KEY': 'Render API key (for triggering)',
        'RENDER_WORKFLOW_SLUG': 'Render workflow slug',
    }

    missing_vars = []

    for var, description in required_vars.items():
        value = os.getenv(var)

        if _is_placeholder_value(var, value):
            print_error(f"{var} not configured ({description})")
            missing_vars.append(var)
        else:
            display_value = value[:10] + '...' if len(value) > 10 else value
            print_success(f"{var} = {display_value}")
    
    # Check optional local dev settings
    use_local_dev = os.getenv('RENDER_USE_LOCAL_DEV', 'false').lower() == 'true'
    local_dev_url = os.getenv('RENDER_LOCAL_DEV_URL', 'http://localhost:8120')
    
    print_info(f"RENDER_USE_LOCAL_DEV = {use_local_dev}")
    print_info(f"RENDER_LOCAL_DEV_URL = {local_dev_url}")
    
    # Dev mode settings
    dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'
    dev_repo_limit = os.getenv('DEV_REPO_LIMIT', '50')
    
    print_info(f"DEV_MODE = {dev_mode}")
    print_info(f"DEV_REPO_LIMIT = {dev_repo_limit}")
    
    if missing_vars:
        print_error(f"\nMissing required environment variables: {', '.join(missing_vars)}")
        print_info("Please update your .env file with valid values.")
        print_info(f"See {ENV_PATH.name} for configuration details.")
        return False
    
    print_success("\nAll required environment variables are configured!")
    
    # Validate GitHub token is actually working
    github_token = os.getenv('GITHUB_ACCESS_TOKEN', '')
    if not validate_github_token(github_token):
        return False
    
    return True


def _handle_oauth_token_expiration() -> bool:
    """Handle expired OAuth token by checking refresh credentials. Returns True if recoverable."""
    has_refresh = bool(os.getenv('GITHUB_REFRESH_TOKEN'))
    has_client_id = bool(os.getenv('GITHUB_CLIENT_ID'))
    has_client_secret = bool(os.getenv('GITHUB_CLIENT_SECRET'))

    if has_refresh and has_client_id and has_client_secret:
        print_info(
            "OAuth refresh credentials are configured — the workflow will attempt auto-refresh.\n"
            "  If that fails, re-authorize with:  cd workflows && python auth_setup.py"
        )
        return True

    missing = [
        v for v, present in [
            ('GITHUB_REFRESH_TOKEN', has_refresh),
            ('GITHUB_CLIENT_ID', has_client_id),
            ('GITHUB_CLIENT_SECRET', has_client_secret),
        ] if not present
    ]
    print_error(
        f"OAuth refresh credentials missing ({', '.join(missing)}).\n"
        "  Cannot auto-renew expired tokens. To fix either:\n"
        "  • Re-authorize:  python workflows/auth_setup.py\n"
        "  • Or switch to a Personal Access Token (PAT) which doesn't expire"
    )
    return False


def validate_github_token(token: str) -> bool:
    """
    Validate that the GitHub token is functional by making a test API call.

    For OAuth tokens (ghu_), also warns about expiration and missing refresh credentials.

    Returns:
        True if token is valid, False if expired/invalid
    """
    print_header("Validating GitHub Token")
    
    is_oauth = token.startswith('ghu_')
    is_pat = token.startswith(('ghp_', 'github_pat_'))
    
    if is_oauth:
        print_info("Token type: OAuth App token (ghu_) — expires 8 hours after creation")
    elif is_pat:
        print_info("Token type: Personal Access Token (PAT) — no expiration")
    else:
        print_warning(f"Token type: Unknown prefix ({token[:4]}...)")
    
    # Test the token with a lightweight API call
    try:
        response = requests.get(
            'https://api.github.com/user',
            headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            username = user_data.get('login', 'unknown')
            remaining = response.headers.get('X-RateLimit-Remaining', '?')
            limit = response.headers.get('X-RateLimit-Limit', '?')
            
            print_success(f"Token valid — authenticated as {username} (rate limit: {remaining}/{limit})")
            
            if is_oauth:
                _check_oauth_refresh_credentials()
            
            return True
        
        elif response.status_code == 401:
            print_error("GitHub token is EXPIRED or INVALID (401 Unauthorized)")

            if is_oauth:
                return _handle_oauth_token_expiration()
            else:
                print_info(
                    "Generate a new token at: https://github.com/settings/tokens/new\n"
                    "  Required scopes: repo, read:org"
                )
                return False
        
        elif response.status_code == 403:
            print_error(
                "GitHub token returned 403 Forbidden — "
                "may indicate rate limiting or insufficient scopes (need: repo, read:org)"
            )
            return False
        
        else:
            print_warning(f"Unexpected GitHub API response: HTTP {response.status_code}")
            return True  # Don't block on unexpected responses
    
    except requests.Timeout:
        print_warning("GitHub API timed out (10s) — proceeding anyway")
        return True
    
    except requests.ConnectionError:
        print_warning("Cannot reach GitHub API — check internet connection. Proceeding anyway")
        return True
    
    except Exception as e:
        print_warning(f"Error validating GitHub token: {e}")
        return True


def _check_oauth_refresh_credentials():
    """Check if OAuth refresh credentials are configured and warn if not."""
    has_refresh = bool(os.getenv('GITHUB_REFRESH_TOKEN'))
    has_client_id = bool(os.getenv('GITHUB_CLIENT_ID'))
    has_client_secret = bool(os.getenv('GITHUB_CLIENT_SECRET'))
    
    if has_refresh and has_client_id and has_client_secret:
        print_success("OAuth auto-refresh credentials configured")
    else:
        missing = [v for v, present in [
            ('GITHUB_REFRESH_TOKEN', has_refresh),
            ('GITHUB_CLIENT_ID', has_client_id),
            ('GITHUB_CLIENT_SECRET', has_client_secret),
        ] if not present]
        print_warning(
            f"OAuth auto-refresh NOT configured (missing: {', '.join(missing)}).\n"
            "  Token will expire after 8 hours with no way to auto-renew.\n"
            "  Add refresh credentials to .env or switch to a PAT (ghp_) token."
        )


def wait_for_server(url: str, timeout: int = 3) -> bool:
    """
    Wait for the local task server to be ready
    
    The Render EA tasks dev server doesn't expose a health endpoint,
    so we just give it a brief grace period to initialize.
    
    Args:
        url: Server URL (for display purposes)
        timeout: Seconds to wait before continuing
    
    Returns:
        Always returns True after timeout
    """
    print_info(f"Giving task server {timeout}s to initialize...")
    time.sleep(timeout)
    print_success("Task server should be ready")
    return True


def start_task_server(port: int = 8120) -> subprocess.Popen:
    """
    Start the local task server in a subprocess
    
    Args:
        port: Port number for the task server
    
    Returns:
        Subprocess handle
    """
    print_header("Starting Local Task Server")
    
    # Build command
    cmd = [
        'render', 'ea', 'tasks', 'dev',
        '--port', str(port),
        '--',
        'python', 'workflows/workflow.py'
    ]
    
    print_info(f"Command: {' '.join(cmd)}")
    print_info(f"Working directory: {PROJECT_ROOT}")
    print_info("Press Ctrl+C to stop both server and trigger processes\n")
    
    # Set up environment for subprocess
    env = os.environ.copy()
    
    # Start subprocess
    process = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # Line buffered
        universal_newlines=True
    )
    
    print_success(f"Task server started (PID: {process.pid})")
    return process


def trigger_workflow() -> subprocess.Popen:
    """
    Trigger the workflow against the local task server
    
    Returns:
        Subprocess handle
    """
    print_header("Triggering Workflow")
    
    cmd = ['python', 'trigger/trigger.py']
    
    print_info(f"Command: {' '.join(cmd)}")
    
    # Set up environment for subprocess
    env = os.environ.copy()
    
    # Start subprocess
    process = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    print_success(f"Trigger process started (PID: {process.pid})")
    return process


def sanitize_output_line(line: str) -> str:
    """
    Sanitize a line of output by removing/replacing problematic characters.
    
    Args:
        line: Raw line from subprocess output
        
    Returns:
        Sanitized line safe for terminal display
    """
    import re
    import unicodedata
    
    # Remove control characters except newline, tab, and carriage return
    # Control characters can cause terminal issues
    sanitized = ''.join(
        char if char in ('\n', '\t', '\r') or not unicodedata.category(char).startswith('C')
        else '?'
        for char in line
    )
    
    # Replace any remaining non-printable or problematic unicode
    # This catches edge cases that might slip through
    sanitized = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '?', sanitized)
    
    # Truncate extremely long lines (likely data dumps)
    max_line_length = 1000
    if len(sanitized) > max_line_length:
        sanitized = sanitized[:max_line_length] + "... (truncated)\n"
    
    return sanitized


def should_display_line(line: str) -> bool:
    """
    Determine if a line should be displayed in terminal output.
    Filters out README content and other non-essential data dumps.
    
    Args:
        line: Line to check
        
    Returns:
        True if line should be displayed, False otherwise
    """
    # Skip empty lines
    if not line or not line.strip():
        return True
    
    # Skip extremely long lines (these are usually data dumps)
    if len(line) > 1000:
        return False
    
    # README detection heuristics - look for markdown patterns
    readme_patterns = [
        r'^#{1,6}\s',  # Markdown headers (# ## ### etc)
        r'```',  # Code fences
        r'img\.shields\.io',  # Badge URLs
        r'badge\.svg',  # Badge images
        r'\[!\[',  # Badge markdown syntax
        r'^\|\s+\w+\s+\|',  # Markdown tables
        r'^[-*]\s+\*\*',  # Markdown lists with bold
        r'<div align=',  # HTML div alignment (common in READMEs)
        r'<picture>',  # Picture tags
        r'<img src=',  # Image tags
        r'!\[.*\]\(.*\)',  # Markdown image syntax
    ]
    
    import re
    for pattern in readme_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return False
    
    # Filter lines with excessive special characters (likely README content)
    special_char_count = sum(1 for c in line if not c.isalnum() and not c.isspace())
    if special_char_count > len(line) * 0.4:  # More than 40% special characters
        return False
    
    # Keep structured log lines (they usually have timestamps, log levels, etc.)
    # These patterns indicate legitimate log output
    log_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # Date pattern
        r'\d{2}:\d{2}:\d{2}',  # Time pattern
        r'\b(INFO|DEBUG|WARNING|ERROR|CRITICAL)\b',  # Log levels
        r'\[SERVER\]',  # Our server prefix
        r'\[TRIGGER\]',  # Our trigger prefix
        r'Task\s+(Completed|Started)',  # Task status
        r'Workflow\s+(started|completed|triggered)',  # Workflow status
        r'Fetching|Processing|Loading|Analyzing',  # Action verbs from our logs
    ]
    
    for pattern in log_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    
    # If line is reasonably short and doesn't match README patterns, display it
    return len(line) < 500


def stream_process_output(process: subprocess.Popen, prefix: str):
    """
    Stream output from a subprocess with a prefix.
    Filters and sanitizes output to prevent README content and special characters
    from causing terminal issues.
    
    Args:
        process: Subprocess to stream from
        prefix: Prefix for log lines
    """
    readme_warning_shown = False
    
    try:
        for line in process.stdout:
            try:
                # Sanitize the line first
                sanitized = sanitize_output_line(line)
                
                # Check if line should be displayed
                if should_display_line(sanitized):
                    print(f"{prefix} {sanitized}", end="")
                elif not readme_warning_shown:
                    # Show a one-time warning about filtered content
                    print(f"{prefix} ... (README content filtered) ...", flush=True)
                    readme_warning_shown = True
                    
            except UnicodeDecodeError as e:
                # Handle encoding errors gracefully
                print(f"{prefix} [Encoding error: {e}]", flush=True)
            except Exception as e:
                # Catch any other line-processing errors
                print(f"{prefix} [Error processing line: {e}]", flush=True)
                
    except Exception as e:
        print_error(f"Error streaming output: {e}")


def cleanup_processes(*processes: subprocess.Popen):
    """Clean up subprocess handles"""
    print_info("\nCleaning up processes...")
    
    for process in processes:
        if process and process.poll() is None:
            print_info(f"Terminating process {process.pid}...")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print_warning(f"Process {process.pid} didn't terminate, killing...")
                process.kill()
            except Exception as e:
                print_error(f"Error cleaning up process {process.pid}: {e}")


def main():
    """Main orchestration function"""
    parser = argparse.ArgumentParser(
        description="Local development orchestrator for Trender workflows"
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8120,
        help='Port for local task server (default: 8120)'
    )
    parser.add_argument(
        '--server-only',
        action='store_true',
        help='Only start the task server (don\'t trigger)'
    )
    parser.add_argument(
        '--trigger-only',
        action='store_true',
        help='Only trigger workflow (assumes server is already running)'
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        help='Don\'t wait for server health check (start immediately)'
    )
    
    args = parser.parse_args()
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Override RENDER_LOCAL_DEV_URL if custom port
    if args.port != 8120:
        os.environ['RENDER_LOCAL_DEV_URL'] = f'http://localhost:{args.port}'
        print_info(f"Using custom port: {args.port}")
    
    # Set RENDER_USE_LOCAL_DEV to true
    os.environ['RENDER_USE_LOCAL_DEV'] = 'true'
    
    server_process = None
    trigger_process = None
    
    try:
        if not args.trigger_only:
            # Start task server
            server_process = start_task_server(port=args.port)
            
            # Wait for server to be ready (unless --no-wait)
            if not args.no_wait:
                server_url = os.getenv('RENDER_LOCAL_DEV_URL', f'http://localhost:{args.port}')
                wait_for_server(server_url, timeout=3)
        
        if args.server_only:
            # Server-only mode: just stream server logs
            print_info("Running in server-only mode. Press Ctrl+C to stop.")
            stream_process_output(server_process, "[SERVER]")
        elif args.trigger_only:
            # Trigger-only mode
            trigger_process = trigger_workflow()
            stream_process_output(trigger_process, "[TRIGGER]")

            # Wait for trigger to complete
            trigger_process.wait()

            if trigger_process.returncode == 0:
                print_success("\nWorkflow triggered successfully!")
            else:
                print_error(f"\nTrigger process exited with code {trigger_process.returncode}")
        else:
            # Full mode: run both server and trigger
            trigger_process = trigger_workflow()

            # Stream output from trigger first (it's quick)
            stream_process_output(trigger_process, "[TRIGGER]")
            trigger_process.wait()

            if trigger_process.returncode == 0:
                print_success("\nWorkflow triggered! Now streaming task server logs...")
                print_info("Press Ctrl+C to stop the server\n")

                # Stream server logs
                stream_process_output(server_process, "[SERVER]")
            else:
                print_error(f"\nTrigger failed with code {trigger_process.returncode}")
    
    except KeyboardInterrupt:
        print_info("\n\nReceived Ctrl+C, shutting down...")
    
    except Exception as e:
        print_error(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cleanup_processes(server_process, trigger_process)
        print_success("\nLocal development session ended.")


if __name__ == "__main__":
    main()

