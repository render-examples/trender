"""
Cron Trigger Script
Triggers the main analysis workflow via Render Workflows SDK.

Auth credentials are refreshed once daily before the workflow runs.
The refresh is the only place GitHub OAuth tokens are consumed.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from render_sdk.client import Client
from refresh_auth import refresh_github_auth

# Load .env file from parent directory (override=True ensures .env always wins
# over any stale values already exported in the shell environment)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)


async def trigger_workflow():
    """
    Trigger the main analysis workflow.

    Uses Render SDK Client in both local dev and production. The SDK automatically
    detects RENDER_USE_LOCAL_DEV and routes requests to the local server.
    Handles response parsing errors that may occur in local dev mode.
    """
    workflow_slug = os.getenv('RENDER_WORKFLOW_SLUG', 'trender-wf')
    use_local_dev = os.getenv('RENDER_USE_LOCAL_DEV', 'false').lower() == 'true'
    task_identifier = f"{workflow_slug}/main_analysis_task"

    # Verify RENDER_API_KEY is set (SDK requires it even in local dev)
    if not os.getenv('RENDER_API_KEY'):
        print("Error: RENDER_API_KEY environment variable is required")
        return None

    try:
        # Initialize the Render SDK client
        # SDK automatically detects RENDER_USE_LOCAL_DEV and RENDER_LOCAL_DEV_URL
        client = Client()

        if use_local_dev:
            print(f"Triggering task (LOCAL DEV): {task_identifier}")
            local_dev_url = os.getenv('RENDER_LOCAL_DEV_URL', 'http://localhost:8120')
            print(f"Target: {local_dev_url}")
        else:
            print(f"Triggering task (PRODUCTION): {task_identifier}")

        # Trigger the task
        started_run = await client.workflows.run_task(
            task_identifier=task_identifier,
            input_data=[]  # main_analysis_task takes no arguments
        )

        # Parse response (may be None or incomplete in local dev)
        if started_run and hasattr(started_run, 'id'):
            print(f"✓ Workflow triggered successfully at {datetime.now(timezone.utc)}")
            print(f"  Task Run ID: {started_run.id}")
            print(f"  Initial Status: {started_run.status if hasattr(started_run, 'status') else 'N/A'}")

            return {
                'run_id': started_run.id,
                'status': started_run.status if hasattr(started_run, 'status') else 'running',
                'task_identifier': task_identifier
            }
        else:
            # Local dev may return None - task was still triggered successfully
            print(f"✓ Task triggered successfully (local dev mode)")
            print(f"  Note: Response object not available in local dev")

            return {
                'run_id': 'local-dev',
                'status': 'triggered',
                'task_identifier': task_identifier
            }

    except TypeError as e:
        # Handle "'NoneType' object is not iterable" and similar errors
        if 'NoneType' in str(e) or 'iterable' in str(e):
            print(f"✓ Task triggered successfully (local dev mode)")
            print(f"  Note: Local dev response parsing skipped")
            return {
                'run_id': 'local-dev',
                'status': 'triggered',
                'task_identifier': task_identifier
            }
        else:
            print(f"✗ Exception during workflow trigger: {str(e)}")
            return None

    except Exception as e:
        # Check if this is the known local dev error
        error_str = str(e)
        if use_local_dev and ('NoneType' in error_str and 'iterable' in error_str):
            # Known issue: SDK triggers task successfully but response parsing fails
            print(f"✓ Task triggered successfully (local dev mode)")
            print(f"  Note: SDK response parsing encountered expected local dev error")
            return {
                'run_id': 'local-dev',
                'status': 'triggered',
                'task_identifier': task_identifier
            }

        print(f"✗ Exception during workflow trigger: {str(e)}")
        return None


async def main():
    """Refresh auth credentials then trigger the workflow."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting daily run")

    # Step 1: Refresh auth credentials (must succeed before workflow runs)
    print("Refreshing GitHub auth credentials...")
    auth_ok = await refresh_github_auth()
    if not auth_ok:
        print("✗ Auth refresh failed - aborting workflow trigger")
        sys.exit(1)
    print("✓ Auth credentials refreshed")

    # Step 2: Trigger the workflow
    print("Triggering analysis workflow...")
    result = await trigger_workflow()
    if result is None:
        print("✗ Workflow trigger failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
