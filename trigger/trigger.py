"""
Cron Trigger Script
Triggers the main analysis workflow via Render Workflows SDK.
"""

import asyncio
import os
from datetime import datetime
from render_sdk.client import Client


async def trigger_workflow():
    """Trigger the main analysis workflow via Render Workflows SDK."""
    workflow_slug = os.getenv('RENDER_WORKFLOW_SLUG', 'trender-workflow')
    
    # Verify RENDER_API_KEY is set (Client uses it automatically)
    if not os.getenv('RENDER_API_KEY'):
        print("Error: RENDER_API_KEY environment variable is required")
        return None

    try:
        # Initialize the Render SDK client (automatically uses RENDER_API_KEY)
        client = Client()

        # Kick off the main analysis task
        # Task identifier format: {workflow-slug}/{task-name}
        task_identifier = f"{workflow_slug}/main-analysis-task"
        
        print(f"Triggering task: {task_identifier}")
        started_run = await client.workflows.run_task(
            task_identifier=task_identifier,
            input_data=[]  # main_analysis_task takes no arguments
        )

        print(f"✓ Workflow triggered successfully at {datetime.utcnow()}")
        print(f"  Task Run ID: {started_run.id}")
        print(f"  Initial Status: {started_run.status}")
        
        return {
            'run_id': started_run.id,
            'status': started_run.status,
            'task_identifier': task_identifier
        }

    except Exception as e:
        print(f"✗ Exception during workflow trigger: {str(e)}")
        return None


if __name__ == "__main__":
    asyncio.run(trigger_workflow())
