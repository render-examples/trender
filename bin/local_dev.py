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
import re
import sys
import subprocess
import time
import signal
import argparse
import traceback
import unicodedata
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

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
    print_info("Validating environment...")

    required_vars = {
        'DATABASE_URL': 'PostgreSQL connection string',
        'RENDER_API_KEY': 'Render API key (for triggering)',
        'RENDER_WORKFLOW_SLUG': 'Render workflow slug',
    }

    oauth_vars = {
        'GITHUB_CLIENT_ID': 'GitHub OAuth App client ID',
        'GITHUB_CLIENT_SECRET': 'GitHub OAuth App client secret',
        'GITHUB_TOKEN_ENCRYPTION_KEY': 'Token encryption key',
    }

    missing_vars = []

    for var, description in required_vars.items():
        value = os.getenv(var)
        if _is_placeholder_value(var, value):
            print_error(f"{var} not configured")
            missing_vars.append(var)

    # Auth: require either GITHUB_PAT or all three OAuth vars
    github_pat = os.getenv('GITHUB_PAT')
    if github_pat:
        print_info("GitHub auth: PAT mode (GITHUB_PAT set)")
    else:
        for var, description in oauth_vars.items():
            value = os.getenv(var)
            if _is_placeholder_value(var, value):
                print_error(f"{var} not configured (set GITHUB_PAT or configure OAuth vars)")
                missing_vars.append(var)

    if missing_vars:
        print_error(f"Missing: {', '.join(missing_vars)}")
        return False

    print_success("Environment validated")
    return True




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
    print_info(f"Waiting {timeout}s for server initialization...")
    time.sleep(timeout)
    return True


def start_task_server(port: int = 8120) -> subprocess.Popen:
    """
    Start the local task server in a subprocess

    Args:
        port: Port number for the task server

    Returns:
        Subprocess handle
    """
    print_info(f"Starting task server on port {port}...")

    # Build command
    cmd = [
        'render', 'ea', 'tasks', 'dev',
        '--port', str(port),
        '--',
        'python', 'workflows/workflow.py'
    ]

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

    print_success(f"Server started (PID: {process.pid})")
    return process


def trigger_workflow() -> subprocess.Popen:
    """
    Trigger the workflow against the local task server

    Returns:
        Subprocess handle
    """
    print_info("Kicking off local run...")

    cmd = ['python', 'trigger/trigger.py']

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

    print_success(f"Local run started (PID: {process.pid})")
    return process


def sanitize_output_line(line: str) -> str:
    """
    Sanitize a line of output by removing/replacing problematic characters.
    
    Args:
        line: Raw line from subprocess output
        
    Returns:
        Sanitized line safe for terminal display
    """
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
    print_info("Cleaning up...")

    for process in processes:
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                print_error(f"Cleanup error: {e}")


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
            print_info("Server-only mode (Ctrl+C to stop)")
            stream_process_output(server_process, "[SERVER]")
        elif args.trigger_only:
            # Trigger-only mode
            trigger_process = trigger_workflow()
            stream_process_output(trigger_process, "[TRIGGER]")
            trigger_process.wait()

            if trigger_process.returncode == 0:
                print_success("Workflow triggered")
            else:
                print_error(f"Trigger failed (exit code {trigger_process.returncode})")
        else:
            # Full mode: run both server and trigger
            trigger_process = trigger_workflow()

            # Stream output from trigger first (it's quick)
            stream_process_output(trigger_process, "[TRIGGER]")
            trigger_process.wait()

            if trigger_process.returncode == 0:
                print_success("Workflow triggered (Ctrl+C to stop server)\n")
                stream_process_output(server_process, "[SERVER]")
            else:
                print_error(f"Trigger failed (exit code {trigger_process.returncode})")
    
    except KeyboardInterrupt:
        print_info("\nShutting down...")

    except Exception as e:
        print_error(f"Error: {e}")
        traceback.print_exc()

    finally:
        cleanup_processes(server_process, trigger_process)
        print_success("Session ended")


if __name__ == "__main__":
    main()

