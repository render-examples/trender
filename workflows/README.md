# Workflows

Python-based ETL pipeline using Render Workflows SDK for distributed task execution.

## Overview

The workflow orchestrates parallel data collection from GitHub's API, processes repositories through a 3-layer data pipeline, and stores results in PostgreSQL for analytics.

## Architecture

```
main_analysis_task (orchestrator)
├── fetch_language_repos (Python)
│   └── analyze_repo_batch
├── fetch_language_repos (TypeScript)
│   └── analyze_repo_batch
├── fetch_language_repos (Go)
│   └── analyze_repo_batch
├── fetch_render_repos
│   └── analyze_repo_batch
└── aggregate_results (ETL: Staging → Analytics)
    └── cleanup_old_data
```

## Task breakdown

### `main_analysis_task`
**Orchestrator** - Spawns 4 parallel tasks (3 languages + Render), then aggregates results.

**Execution modes:**
- **Production**: Full pipeline (all languages + Render)
- **Dev mode**: Python only (`DEV_MODE=true` + `DEV_REPO_LIMIT=5`)

**Returns:**
```python
{
    'repos_processed': int,
    'execution_time': float,
    'cleanup_stats': dict,
    'trace_id': str,
    'success': bool
}
```

### `fetch_language_repos(language: str)`
**Parallel task** - Fetches trending repos for Python, TypeScript, or Go.

**Process:**
1. Search GitHub API (repos updated in last 30 days, created in last 180 days)
2. Take top 25 repos (sorted by stars)
3. Fetch READMEs in parallel
4. Store in raw layer
5. Spawn `analyze_repo_batch` subtask

**Returns:**
```python
{
    'repos': List[Dict],  # Enriched repo data
    'subtasks': List[Dict],  # Timing metadata
    'started_at': str,  # ISO timestamp
    'completed_at': str
}
```

### `fetch_render_repos()`
**Parallel task** - Discovers Render projects via code search.

**Detection strategy:**
- Code search for `render.yaml` in repository root only
- Repos created within last 18 months
- Target: 25 projects

**Process:**
1. Search GitHub for `filename:render.yaml path:/ language:yaml`
2. Fetch READMEs in parallel
3. Store in raw layer (assigned `language='render'`)
4. Spawn `analyze_repo_batch` subtask

### `analyze_repo_batch(repos: List[Dict], readme_contents: Dict)`
**Subtask** - Analyzes repos in batches of 10.

**Per repository:**
1. Validate required fields (full_name, language, created_at, updated_at)
2. Build enriched data structure
3. Parse ISO datetime strings to timezone-aware objects
4. Store in staging layer (`stg_repos_validated`)

**Error handling:** Continues on individual repo failures (logged but not fatal)

### `aggregate_results(all_results, db_pool, execution_start, trace)`
**ETL pipeline** - Extracts from staging, calculates scores, loads to analytics.

**Process:**
1. Extract top 50 repos per language (balanced)
2. Extract ALL Render repos (`language='render'`)
3. Calculate momentum scores (70% recency + 30% normalized stars)
4. Load to analytics layer:
   - `dim_repositories` (upsert with SCD Type 2)
   - `fact_repo_snapshots` (daily snapshot with momentum score)
   - `fact_render_usage` (for Render repos only)
5. Run data retention cleanup

**Scoring formula:**
```python
recency_score = exponential_decay(repo_age_days)  # 1.0 for ≤14 days, decay to 0.01
normalized_stars = stars / max_stars_in_category
momentum_score = (recency_score * 0.7) + (normalized_stars * 0.3)
```

### `cleanup_old_data(db_pool)`
**Maintenance task** - Applies tiered data retention policy.

**Retention windows:**
- Raw layer: 7 days
- Staging layer: 7 days
- Analytics layer: 30 days

**Error handling:** Failures logged but don't break workflow

## Files

| File | Purpose |
|------|---------|
| `workflow.py` | Main workflow with @task decorators |
| `github_api.py` | Async GitHub API client (search, fetch) |
| `connections.py` | Shared resource management (DB pool, HTTP session) |
| `auth_setup.py` | Interactive GitHub auth token generator |
| `etl/extract.py` | Raw layer data ingestion |
| `requirements.txt` | Python dependencies |

## Environment variables

```bash
# Required
DATABASE_URL=postgresql://...
GITHUB_ACCESS_TOKEN=ghp_...

# Optional (development)
DEV_MODE=true           # Runs Python task only
DEV_REPO_LIMIT=5        # Processes 5 repos instead of 25

# Optional (local dev)
RENDER_USE_LOCAL_DEV=true
RENDER_LOCAL_DEV_URL=http://localhost:8120
```

## Running locally

### Option 1: Quick start (recommended)
```bash
python ../bin/local_dev.py
```

### Option 2: Manual
```bash
# Terminal 1: Start task server
cd workflows
pip install -r requirements.txt
python workflow.py  # Listens on port 8120

# Terminal 2: Trigger workflow
cd trigger
python trigger.py
```

## Running on Render

Workflows are triggered via:
1. **Cron job**: Hourly at 14:00 UTC (6 AM PST)
2. **Manual**: Dashboard → Workflows → trender-wf → Run Task
3. **API**: `python trigger/trigger.py`

## Debugging

**Check workflow status:**
```bash
# Via logs
render logs --service trender-wf

# Via database
psql $DATABASE_URL -c "SELECT * FROM fact_workflow_runs ORDER BY started_at DESC LIMIT 1;"
```

**Inspect trace tree:**
```python
# Query the task_tree JSONB column
SELECT run_id, status, task_tree FROM fact_workflow_runs
WHERE run_id = 'wfr_...';
```

**Common issues:**

| Issue | Solution |
|-------|----------|
| `GITHUB_ACCESS_TOKEN not set` | Add token to Render environment variables |
| Connection refused | Check DATABASE_URL is correct |
| Rate limit errors | Verify token scopes include `repo`, `read:org` |
| No repos returned | GitHub API may be rate limited or down |

## Data flow

```
GitHub API
    ↓
raw_github_repos (JSONB)
    ↓
stg_repos_validated (cleaned)
    ↓
dim_repositories + fact_repo_snapshots (dimensional model)
    ↓
Dashboard views
```

## Performance

- **Execution time**: 10-20 seconds for ~150 repos
- **Parallelism**: 4 concurrent tasks
- **Batching**: Repos analyzed in batches of 10
- **README fetching**: Parallel requests to minimize API latency

## Testing

```bash
# Fast iteration: Dev mode (Python only, 5 repos)
export DEV_MODE=true
export DEV_REPO_LIMIT=5
python workflow.py

# Full pipeline locally
unset DEV_MODE
python ../bin/local_dev.py
```

## Workflow tracing

The `WorkflowTrace` class tracks execution with hierarchical task timing:

```python
{
    'name': 'main_analysis_task',
    'started_at': '2026-02-02T12:00:00Z',
    'completed_at': '2026-02-02T12:00:15Z',
    'status': 'completed',
    'children': [
        {'name': 'fetch_language_repos', 'language': 'Python', ...},
        {'name': 'fetch_language_repos', 'language': 'TypeScript', ...},
        ...
    ]
}
```

Stored in `fact_workflow_runs` for observability.

## Dependencies

See `requirements.txt`:
- `render-sdk`: Workflows SDK with @task decorators
- `asyncpg`: Async PostgreSQL driver
- `aiohttp`: Async HTTP client
- `python-dotenv`: Environment variable management

## Contributing

1. Make changes to workflow logic
2. Test locally: `python ../bin/local_dev.py`
3. Deploy: Push to GitHub (auto-deploy enabled)
4. Monitor: Dashboard → Workflows → Logs

