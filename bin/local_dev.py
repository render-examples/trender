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
from dotenv import load_dotenv
import requests

# Get project root (parent of bin/)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / '.env'

# Load environment variables from .env
load_dotenv(dotenv_path=ENV_PATH)


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(message: str):
    """Print a colored header message"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}", file=sys.stderr)


def print_info(message: str):
    """Print an info message"""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print a warning message"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


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
    
    # Define placeholder patterns for each variable type
    placeholder_patterns = {
        'DATABASE_URL': ['postgresql://username:password@host', 'postgresql://user:pass@localhost'],
        'GITHUB_ACCESS_TOKEN': ['ghp_your_access_token_here', 'github_pat_your'],
        'RENDER_API_KEY': ['rnd_your_render_api_key_here'],
        'RENDER_WORKFLOW_SLUG': ['your_workflow_slug_here', 'trender-wf-example'],
    }
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        
        # Check if value is missing or is a placeholder
        is_placeholder = False
        if not value:
            is_placeholder = True
        elif var in placeholder_patterns:
            # Check if value matches any placeholder pattern for this variable
            for pattern in placeholder_patterns[var]:
                if value.startswith(pattern) or value == pattern:
                    is_placeholder = True
                    break
        
        if is_placeholder:
            print_error(f"{var} not configured ({description})")
            missing_vars.append(var)
        else:
            # Show partial value for security
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


def stream_process_output(process: subprocess.Popen, prefix: str):
    """
    Stream output from a subprocess with a prefix
    
    Args:
        process: Subprocess to stream from
        prefix: Prefix for log lines
    """
    try:
        for line in process.stdout:
            print(f"{prefix} {line}", end="")
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
            stream_process_output(server_process, f"{Colors.OKBLUE}[SERVER]{Colors.ENDC}")
        elif args.trigger_only:
            # Trigger-only mode
            trigger_process = trigger_workflow()
            stream_process_output(trigger_process, f"{Colors.OKGREEN}[TRIGGER]{Colors.ENDC}")
            
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
            stream_process_output(trigger_process, f"{Colors.OKGREEN}[TRIGGER]{Colors.ENDC}")
            trigger_process.wait()
            
            if trigger_process.returncode == 0:
                print_success("\nWorkflow triggered! Now streaming task server logs...")
                print_info("Press Ctrl+C to stop the server\n")
                
                # Stream server logs
                stream_process_output(server_process, f"{Colors.OKBLUE}[SERVER]{Colors.ENDC}")
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

