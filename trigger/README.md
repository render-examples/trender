# Trigger

Cron trigger script that initiates workflow execution via Render SDK.

## Overview

Lightweight Python script that triggers the `main_analysis_task` workflow using the Render Workflows SDK. Can be run manually or via cron job.

## Files

| File | Purpose |
|------|---------|
| `trigger.py` | Main trigger script using Render SDK |
| `requirements.txt` | Python dependencies |

## How it works

```python
# 1. Initialize Render client (uses RENDER_API_KEY from env)
client = Client()

# 2. Trigger workflow task
task_identifier = f"{workflow_slug}/main_analysis_task"
run = await client.workflows.run_task(
    task_identifier=task_identifier,
    input_data=[]  # No arguments needed
)

# 3. Return run metadata
print(f"Task Run ID: {run.id}")
print(f"Status: {run.status}")
```

## Environment variables

```bash
# Required
RENDER_API_KEY=rnd_...         # From dashboard.render.com/u/settings#api-keys
RENDER_WORKFLOW_SLUG=trender-wf  # Your workflow slug

# Optional (for local dev)
RENDER_USE_LOCAL_DEV=true
RENDER_LOCAL_DEV_URL=http://localhost:8120
```

**Note:** The script loads `.env` from the parent directory automatically.

## Running manually

### Quick start

```bash
cd trigger
pip install -r requirements.txt

# Set environment variables
export RENDER_API_KEY=your_api_key
export RENDER_WORKFLOW_SLUG=trender-wf

# Run trigger
python trigger.py
```

**Expected output:**

```
Triggering task: trender-wf/main_analysis_task
✓ Workflow triggered successfully at 2026-02-02 12:00:00
  Task Run ID: run_abc123xyz
  Initial Status: running
```

### Using .env file

```bash
# Create .env in project root
echo "RENDER_API_KEY=rnd_..." >> ../.env
echo "RENDER_WORKFLOW_SLUG=trender-wf" >> ../.env

# Run (automatically loads .env)
python trigger.py
```

## Cron job usage

The trigger script is designed to run as a Render cron job (see `render.yaml`):

```yaml
- type: cron
  name: trender-cron
  runtime: python
  schedule: "0 14 * * *"  # Daily at 14:00 UTC (6 AM PST)
  buildCommand: cd trigger && pip install -r requirements.txt
  startCommand: cd trigger && python trigger.py
  envVars:
    - key: RENDER_WORKFLOW_SLUG
      sync: false
    - key: RENDER_API_KEY
      sync: false
```

**Schedule format:** Standard cron syntax
- `0 14 * * *` = Daily at 14:00 UTC
- `*/15 * * * *` = Every 15 minutes
- `0 */2 * * *` = Every 2 hours

## Local development

When testing workflows locally, set `RENDER_USE_LOCAL_DEV`:

```bash
# .env file
RENDER_USE_LOCAL_DEV=true
RENDER_LOCAL_DEV_URL=http://localhost:8120
RENDER_WORKFLOW_SLUG=trender-wf
```

**Workflow:**
1. Start local task server: `cd workflows && python workflow.py`
2. Run trigger: `cd trigger && python trigger.py`

**Or use orchestrator:** `python bin/local_dev.py`

## Return value

The script returns a dictionary with workflow run metadata:

```python
{
    'run_id': 'run_abc123xyz',
    'status': 'running',  # or 'completed', 'failed'
    'task_identifier': 'trender-wf/main_analysis_task'
}
```

## Error handling

**Missing API key:**
```
Error: RENDER_API_KEY environment variable is required
```

**Invalid workflow slug:**
```
✗ Exception during workflow trigger: Workflow not found
```

**Network errors:**
```
✗ Exception during workflow trigger: Connection timeout
```

## Checking workflow status

After triggering, monitor via:

### 1. Render Dashboard
- Go to [Workflows section](https://dashboard.render.com)
- Select `trender-wf`
- View recent runs and logs

### 2. Database Query
```bash
psql $DATABASE_URL -c "
SELECT 
    run_id, 
    status, 
    started_at, 
    completed_at, 
    repos_processed,
    execution_time_seconds
FROM fact_workflow_runs
ORDER BY started_at DESC
LIMIT 1;
"
```

### 3. Dashboard API
```bash
curl https://trender-dashboard.onrender.com/api/workflow-status
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "RENDER_API_KEY not set" | Export key or add to `.env` file |
| "Connection refused" | Check RENDER_LOCAL_DEV_URL if using local dev |
| "Workflow not found" | Verify RENDER_WORKFLOW_SLUG matches dashboard |
| Script hangs | Check network connectivity to Render API |
| "Task not found" | Ensure workflow is deployed with `main_analysis_task` |

## Dependencies

See `requirements.txt`:

```txt
render-sdk>=0.1.0  # Render Workflows SDK
python-dotenv      # Environment variable loading
```

**Install:**
```bash
pip install -r requirements.txt
```

## Programmatic usage

Import and use in other Python scripts:

```python
from trigger import trigger_workflow
import asyncio

# Trigger workflow
result = asyncio.run(trigger_workflow())

if result:
    print(f"Workflow started: {result['run_id']}")
else:
    print("Failed to trigger workflow")
```

## Contributing

1. Test locally: `python trigger.py`
2. Verify workflow runs successfully
3. Check logs for any errors
4. Deploy: Push to GitHub (auto-deploy)

