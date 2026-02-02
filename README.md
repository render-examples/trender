# Trender: GitHub Trending Analytics Platform

A batch analytics platform with a **3-layer data engineering pipeline** (Raw → Staging → Analytics) that analyzes trending GitHub repositories across 3 programming languages (Python, TypeScript/Next.js, and Go) plus the Render ecosystem. Leverages Render Workflows' distributed task execution to process data in parallel, storing results in a dimensional model for high-performance analytics.

## Key Features

- **Multi-Language Analysis**: Tracks Python, TypeScript/Next.js, Go, and Render ecosystem repositories
- **3-Layer Data Pipeline**: Raw ingestion → Staging validation → Analytics dimensional model
- **Parallel Processing**: 4 concurrent workflow tasks using Render Workflows SDK
- **Render Ecosystem Spotlight**: Dedicated showcase for Render-deployed projects (identified by `language='render'`)
- **Real-time Dashboard**: Next.js 14 dashboard with analytics visualizations
- **Hourly Updates**: Automated cron job triggers workflow execution

## Architecture Note

**Render Repos Identification**: Repositories with `render.yaml` in their root directory are assigned `language='render'` (lowercase) in the database, allowing clean identification without a separate boolean flag. This simplifies queries and eliminates the need for maintaining dual identification logic.

## Architecture

```mermaid
graph TD
    A[Cron Job Hourly] --> B[Workflow Orchestrator]
    B --> C[Python Analyzer]
    B --> D[TypeScript Analyzer]
    B --> E[Go Analyzer]
    B --> F[Render Ecosystem]
    C --> G[Raw Layer JSONB]
    D --> G
    E --> G
    F --> G
    G --> H[Staging Layer Validated]
    H --> I[Analytics Layer Fact/Dim]
    I --> J[Next.js Dashboard]
```

## Tech Stack

**Backend (Workflows)**
- Python 3.11+
- Render Workflows SDK with `@task` decorators
- asyncpg for PostgreSQL
- aiohttp for async API calls
- GitHub REST API

**Frontend (Dashboard)**
- Next.js 14.2 (App Router)
- TypeScript
- Tailwind CSS
- Recharts for visualizations
- PostgreSQL (pg)

**Infrastructure**
- Render Workflows (task execution)
- Render Cron Job (hourly trigger)
- Render Web Service (Next.js dashboard)
- Render PostgreSQL (data storage)

## Project Structure

```
trender/
├── workflows/
│   ├── workflow.py           # Main workflow with @task decorators
│   ├── github_api.py         # Async GitHub API client
│   ├── connections.py        # Shared resource management
│   ├── render_detection.py  # Render usage detection
│   ├── etl/
│   │   └── extract.py        # Raw layer extraction
│   └── requirements.txt
├── trigger/
│   ├── trigger.py            # Cron trigger script
│   └── requirements.txt
├── dashboard/
│   ├── app/                  # Next.js App Router pages
│   ├── components/           # Reusable UI components
│   ├── lib/
│   │   ├── db.ts            # Database utilities
│   │   └── formatters.ts    # Data formatting helpers
│   └── package.json
├── database/
│   ├── schema/
│   │   ├── 01_raw_layer.sql
│   │   ├── 02_staging_layer.sql
│   │   ├── 03_analytics_layer.sql
│   │   └── 04_views.sql
│   └── init.sql
├── render.yaml
├── .env.example
└── README.md
```

## Quick Start - Trigger a Workflow

If you've already completed the setup and just want to trigger a workflow run:

```bash
# Navigate to trigger directory
cd trigger

# Set environment variables
export RENDER_API_KEY=your_api_key
export RENDER_WORKFLOW_SLUG=trender-wf

# Install dependencies and run
pip install -r requirements.txt
python trigger.py
```

Or use the Render Dashboard: **Workflows** → **trender-wf** → **Tasks** → **main_analysis_task** → **Run Task**

---

## Setup Instructions

### Prerequisites

- GitHub authentication (Personal Access Token or OAuth App - covered in step 2)
- Render account
- Node.js 18+ (for dashboard)
- Python 3.11+ (for workflows)

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd trender
```

### 2. GitHub Authentication Setup

Trender needs a GitHub access token to fetch repository data. You can choose between two authentication methods:

---

#### 🎯 **Option A: Personal Access Token (PAT) - Recommended**

**Best for:** Individual developers, quick setup, local development

This is the **simplest method** - just create a token from GitHub settings.

##### Step 1: Run the auth setup script

```bash
cd workflows
pip install -r requirements.txt
python auth_setup.py
```

##### Step 2: Choose option [1] for PAT

##### Step 3: Follow the interactive prompts:
1. Open https://github.com/settings/tokens/new in your browser
2. Configure the token:
   - **Note**: `Trender Analytics Access`
   - **Expiration**: `No expiration` (or your preference)
   - **Scopes**:
     - ✓ `repo` (Full control of private repositories)
     - ✓ `read:org` (Read org and team membership)
3. Click **"Generate token"**
4. Copy the token (starts with `ghp_` or `github_pat_`)
5. Paste it into the terminal when prompted

##### Step 4: Save your token

The script will verify your token and display:

```bash
✅ SUCCESS! Your GitHub access token (PAT):
============================================================

ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

============================================================
Add this to your .env file:
GITHUB_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Add the token to your `.env` file:
```bash
GITHUB_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**✅ Done!** Skip to Step 3.

---

#### 🔐 **Option B: OAuth App - Advanced**

**Best for:** Team setups, production deployments, requiring user authorization flow

##### Step 1: Create GitHub OAuth App

1. Go to https://github.com/settings/developers
2. Click **"New OAuth App"**
3. Fill in the details:
   - **Application name**: `Trender Analytics`
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:8000/callback`
4. Click **"Register application"**
5. Note your **Client ID** (starts with `Ov23` or `Iv1.`)
6. Click **"Generate a new client secret"** and save it

##### Step 2: Add OAuth credentials to .env

```bash
GITHUB_CLIENT_ID=Ov23xxxxx_or_Iv1.xxxxx
GITHUB_CLIENT_SECRET=your_secret_here
```

##### Step 3: Run the auth setup script

```bash
cd workflows
pip install -r requirements.txt
python auth_setup.py
```

Choose option [2] for OAuth, then:
1. The script starts a local server on port 8000
2. Your browser opens to GitHub's authorization page
3. Click **"Authorize"** to approve
4. The script exchanges the auth code for a token
5. Your `GITHUB_ACCESS_TOKEN` is displayed

##### Step 4: Save your token

Add the token to your `.env` file:
```bash
GITHUB_ACCESS_TOKEN=gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 🔒 Security Best Practices (Both Methods)

- ✅ Tokens don't expire (unless you set expiration on PAT)
- ✅ Never commit tokens to version control (`.env` is in `.gitignore`)
- ✅ Token scopes: `repo` and `read:org` only
- ✅ Revoke access anytime at https://github.com/settings/tokens
- ⚠️  Treat tokens like passwords

#### 🐛 Troubleshooting

**PAT Issues:**
- **Token doesn't start with `ghp_`**: Classic tokens start with `ghp_`, fine-grained tokens with `github_pat_`
- **API returns 401**: Token may be expired or revoked. Generate a new one.
- **Rate limit errors**: Ensure token has proper scopes selected

**OAuth Issues:**
- **Port 8000 in use**: Run `lsof -ti:8000 | xargs kill -9`, then try again
- **"Redirect URI mismatch"**: Ensure callback URL in OAuth app is exactly `http://localhost:8000/callback`
- **Browser doesn't open**: Manually visit the URL shown in the terminal
- **"Bad verification code"**: Code expires quickly. Run `python auth_setup.py` again

**Both Methods:**
- **Token verification fails**: Check your internet connection
- **Need to regenerate**: Revoke old token at https://github.com/settings/tokens and generate new one

### 3. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

Your `.env` file should now contain (from step 2):

**If you used PAT (Option A):**
```bash
GITHUB_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**If you used OAuth (Option B):**
```bash
GITHUB_CLIENT_ID=Ov23xxxxx_or_Iv1.xxxxx
GITHUB_CLIENT_SECRET=your_secret_here
GITHUB_ACCESS_TOKEN=gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Other required variables (add as you complete the setup):
- `DATABASE_URL`: PostgreSQL connection string (from step 4)
- `RENDER_API_KEY`: Render API key (from https://dashboard.render.com/u/settings#api-keys)
- `RENDER_WORKFLOW_SLUG`: `trender-wf` (or your workflow slug from step 6)

### 4. Create PostgreSQL Database on Render

1. Go to Render Dashboard
2. Create new PostgreSQL database:
   - **Name**: `trender-db`
   - **Database Name**: `trender`
   - **Plan**: `basic_256mb` (or higher for production)
3. Note the connection string for `DATABASE_URL`

### 5. Initialize Database Schema

#### Option 1: Using the setup script (Recommended)

The `db_setup.sh` script provides a user-friendly way to initialize the database with connection checking, error handling, and colored output:

```bash
# Make the script executable (first time only)
chmod +x bin/db_setup.sh

# Run the setup script
# The script will automatically load DATABASE_URL from your .env file
./bin/db_setup.sh

# Or provide DATABASE_URL directly:
DATABASE_URL=YOUR_DATABASE_URL ./bin/db_setup.sh
```

Expected output:
```
🚀 Trender Database Setup
==========================

📄 Loading environment variables from .env file...
✓ Environment variables loaded

📁 Project root: /path/to/trender

🔍 Checking database connection...
✓ Database connection successful

📊 Initializing database schema...
Running: database/init.sql

Creating Raw Layer tables...
Creating Staging Layer tables...
Creating Analytics Layer tables...
Creating Analytics Views...

✅ Database setup completed successfully!
```

#### Option 2: Using the init.sql script directly

```bash
# Connect to your Render PostgreSQL instance and run the initialization script
cd database
psql $DATABASE_URL -f init.sql
```

#### Option 3: Run schema files individually

If you prefer to run the schema files one at a time:

```bash
cd database
psql $DATABASE_URL -f schema/01_raw_layer.sql
psql $DATABASE_URL -f schema/02_staging_layer.sql
psql $DATABASE_URL -f schema/03_analytics_layer.sql
psql $DATABASE_URL -f schema/04_views.sql
```

#### What gets created:

**Raw Layer:**
- `raw_github_repos`: Stores complete GitHub API responses (JSONB format)
- `raw_repo_metrics`: Stores repository metrics (commits, issues, contributors)

**Staging Layer:**
- `stg_repos_validated`: Cleaned and validated repository data
- `stg_render_enrichment`: Render-specific metadata (service types, complexity, categories)

**Analytics Layer:**
- **Dimension tables**: 
  - `dim_repositories`: Repository master data with SCD Type 2 history
  - `dim_languages`: Language metadata
  - `dim_render_services`: Render service type reference data (web, worker, cron, etc.)
- **Fact tables**: 
  - `fact_repo_snapshots`: Daily snapshots of repo metrics and momentum scores
  - `fact_render_usage`: Render service adoption by repository

**Views:**
- `analytics_trending_repos_current`: Current top trending repos across all languages
- `analytics_render_showcase`: Render ecosystem showcase with enrichment
- `analytics_language_rankings`: Per-language rankings with Render adoption stats
- `analytics_render_services_adoption`: Service type adoption statistics
- `analytics_language_trends`: Language-level aggregated statistics
- `analytics_repo_history`: Historical trends for charting

**Total: 9 tables + 6 views**

#### Verify Database Initialization

Check that all tables were created successfully:

```bash
psql $DATABASE_URL -c "\dt"
```

You should see 9 tables across the raw, stg, dim, and fact prefixes.

#### Apply Cleanup Migration (If Upgrading)

If you're upgrading from an older version that had workflow execution tracking, run the cleanup script:

```bash
psql $DATABASE_URL -f database/cleanup_workflow_tracking.sql
```

This removes the unused `fact_workflow_executions` table and `analytics_workflow_performance` view.

#### Troubleshooting

- **"DATABASE_URL not set"**: Ensure you have a `.env` file with `DATABASE_URL` or export it in your shell
- **"Could not connect to database"**: Verify your `DATABASE_URL` is correct and the Render PostgreSQL instance is active
- **Permission denied**: Make sure you're using the connection string with full admin privileges
- **Tables already exist**: Drop the database and recreate it, or use `DROP TABLE IF EXISTS` statements
- **"No such file or directory" errors**: Make sure you're running from the correct directory (use the `db_setup.sh` script to avoid this issue)

### 6. Deploy Services via render.yaml

The `render.yaml` file defines:
- **Web Service**: Next.js dashboard (`trender-dashboard`)
- **Workflow**: Main analytics pipeline (`trender-wf`)
- **Cron Job**: Hourly workflow trigger (`trender-analyzer-cron`)
- **Database**: PostgreSQL instance (`trender-db`)

Deploy to Render:
1. Push your code to GitHub
2. In Render Dashboard, click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will automatically detect and deploy all services from `render.yaml`

Or use the Render CLI:
```bash
render blueprint launch
```

### 7. Configure Environment Variables in Render

After deploying via `render.yaml`, add your GitHub access token to the **workflow service** (`trender-wf`) in the Render Dashboard:

1. Go to your `trender-wf` workflow in Render Dashboard
2. Navigate to **Environment** tab
3. Add:
   - `GITHUB_ACCESS_TOKEN`: The token you generated in step 2 (starts with `ghp_` or `gho_` or `github_pat_`)
   - `DATABASE_URL`: Automatically connected from the database (no action needed)

**Important:** After adding the token, trigger a manual deploy:
- Click **"Manual Deploy"** → **"Clear build cache & deploy"**
- This ensures the environment variables are available to your workflow tasks

**Note:** You only need `GITHUB_ACCESS_TOKEN` in Render. If you used OAuth, you don't need to add `GITHUB_CLIENT_ID` or `GITHUB_CLIENT_SECRET` to Render.

### 8. Trigger Workflow Runs

There are three ways to trigger a workflow run to populate data:

#### Method 1: Using the Trigger Script (Recommended)

The `trigger/trigger.py` script uses the Render SDK to trigger workflows programmatically:

```bash
cd trigger

# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export RENDER_API_KEY=your_render_api_key
export RENDER_WORKFLOW_SLUG=trender-wf  # Your workflow slug from Render dashboard

# Run the trigger script
python trigger.py
```

Expected output:
```
Triggering task: trender-wf/main-analysis-task
✓ Workflow triggered successfully at 2026-01-23 12:00:00
  Task Run ID: run_abc123xyz
  Initial Status: running
```

#### Method 2: Using the Render Dashboard

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Navigate to **Workflows** section
3. Select your `trender-wf` workflow
4. Click on the **"main-analysis-task"** task
5. Click **"Run Task"** button
6. Monitor the task execution in real-time

#### Method 3: Using Render CLI

If you have the Render CLI installed:

```bash
# Install Render CLI (if not already installed)
npm install -g @render-inc/cli

# Login to Render
render login

# Trigger the workflow
render workflows trigger trender-wf main-analysis-task
```

#### Verify Workflow Execution

Check the workflow status:

1. **Via Dashboard**: Go to Workflows → trender-wf → View recent runs
2. **Via Script**: The trigger script outputs the Task Run ID
3. **Via Database**: Query the `dim_repositories` table to see loaded data:

```bash
psql $DATABASE_URL -c "SELECT language, COUNT(*) as count FROM dim_repositories WHERE is_current = TRUE GROUP BY language;"
```

Expected workflow completion time: **10-20 seconds** for ~150 repositories across 3 languages + Render ecosystem

#### Troubleshooting

- **"RENDER_API_KEY not set"**: Export your API key from [Render Settings](https://dashboard.render.com/u/settings#api-keys)
- **"Task not found"**: Verify your workflow slug is `trender-wf` and that the workflow is deployed
- **"Connection refused"**: Check that `DATABASE_URL` is correct and the database is running
- **Workflow fails**: Check the Render dashboard logs under Workflows → trender-wf → Logs for detailed error messages
- **"GITHUB_ACCESS_TOKEN not set"**: Ensure you added the token to the workflow service environment variables (step 7)

### 9. Access Dashboard

Once the workflow completes, access your dashboard at:
```
https://trender-dashboard.onrender.com
```

You should see:
- Top trending repositories across Python, TypeScript, and Go
- Render ecosystem projects
- Momentum scores and analytics
- Historical trends

## Data Pipeline Layers

### Layer 1: Raw Ingestion
- Stores complete GitHub API responses
- Tables: `raw_github_repos`, `raw_repo_metrics`
- Purpose: Audit trail and reprocessing capability

### Layer 2: Staging (Validation)
- Cleaned and validated data
- Tables: `stg_repos_validated`, `stg_render_enrichment`
- Business rules applied
- **Render enrichment data**: service types, complexity scores, categories, blueprint indicators

### Layer 3: Analytics (Dimensional Model)
- **Dimensions**: `dim_repositories`, `dim_languages`, `dim_render_services`
- **Facts**: `fact_repo_snapshots`, `fact_render_usage`
- **Views**: Pre-aggregated analytics for dashboard
- **Render analytics**: Service adoption metrics, complexity distributions, blueprint quality indicators

## Workflow Tasks

The workflow consists of 4 main tasks decorated with `@task`:

1. **`main_analysis_task`**: Orchestrator that spawns parallel tasks and coordinates the ETL pipeline
2. **`fetch_language_repos`**: Fetches and stores trending repos for Python, TypeScript, or Go
3. **`analyze_repo_batch`**: Analyzes repos in batches of 10, enriching with detailed metrics
4. **`fetch_render_repos`**: Fetches Render ecosystem repositories using multi-strategy search

The orchestrator runs 4 parallel tasks (3 languages + 1 Render ecosystem), then aggregates results through the ETL pipeline (Extract from staging → Calculate scores → Load to analytics).

### Render Ecosystem Discovery

The `fetch_render_repos` task uses a 2-strategy approach to discover Render projects:

1. **Code Search for render.yaml** - Uses GitHub's code search API to find repositories with `render.yaml` **in the root directory only**. This ensures we only capture repos that are properly configured for Render deployment. Results are sorted by stars descending.
2. **Topic Search** - Finds community repos tagged with `render-blueprints` topic

This approach ensures accuracy (only repos with actual render.yaml files) and maximizes coverage of community projects. When a Render repo is found, the system:

- Fetches and parses the `render.yaml` file to extract service configurations
- Calculates complexity scores based on number and type of services
- Categorizes projects (official, community, blueprint)
- Stores enrichment data in `stg_render_enrichment` table
- Populates `fact_render_usage` for service adoption analytics

## Metrics Calculated

- **Momentum Score**: Composite score combining:
  - **50% Normalized Stars**: Stars normalized within dataset (general repos vs Render repos scored separately)
  - **50% Recency Score**: Based on repository creation date
    - 1.0 for repos ≤ 30 days old
    - 0.75 for repos 31-60 days old
    - 0.5 for repos 61-90 days old
    - 0.0 for repos > 90 days old
- **Note**: Activity metrics (commits, issues, contributors) are collected but not used in scoring

## Development

### Local Development - Workflows

```bash
cd workflows
pip install -r requirements.txt
python workflow.py
```

### Local Development - Dashboard

```bash
cd dashboard
npm install
npm run dev
# Access at http://localhost:3000
```

### Run Database Migrations

If you need to recreate or update the schema:

**Option 1: Using the setup script (Recommended)**
```bash
./bin/db_setup.sh
```

**Option 2: Using psql directly**
```bash
cd database
psql $DATABASE_URL -f init.sql
```

**Option 3: Run individual schema files**
```bash
cd database
psql $DATABASE_URL -f schema/01_raw_layer.sql
psql $DATABASE_URL -f schema/02_staging_layer.sql
psql $DATABASE_URL -f schema/03_analytics_layer.sql
psql $DATABASE_URL -f schema/04_views.sql
```

If upgrading from an older version, apply the cleanup migration:

```bash
psql $DATABASE_URL -f database/cleanup_workflow_tracking.sql
```

## Data Retention

Trender implements a **tiered data retention policy** to maintain predictable storage costs while preserving data needed for debugging and analytics.

### Retention Windows

| Layer | Retention Period | Purpose |
|-------|-----------------|---------|
| **Raw Layer** | 7 days | Debugging and reprocessing capability |
| **Staging Layer** | 7 days | ETL audit trail for data quality issues |
| **Analytics Layer** | 30 days | Trending analysis and dashboard history |

### How It Works

**Automatic Cleanup**: The retention cleanup runs automatically after each successful workflow execution. Old data is deleted according to the retention windows above.

**What Gets Cleaned Up**:
- `raw_github_repos` and `raw_repo_metrics`: Data older than 7 days
- `stg_repos_validated` and `stg_render_enrichment`: Data older than 7 days
- `fact_repo_snapshots` and `fact_render_usage`: Snapshots older than 30 days
- `dim_repositories`: Historical versions (SCD Type 2) older than 30 days

### Storage Impact

With the retention policy in place:
- **Steady-state storage**: ~3,000 repository snapshots (30 days × ~100 repos/day)
- **No unbounded growth**: Data automatically ages out
- **Sufficient for trends**: 1 month of historical data for dashboard

Without retention (for comparison):
- **30 days**: ~3,000 snapshots
- **90 days**: ~9,000 snapshots
- **1 year**: ~36,500 snapshots (12x more!)

### Manual Cleanup

If you need to run cleanup manually (e.g., for testing or maintenance):

```bash
# Using the standalone script (recommended)
./bin/cleanup_data.sh

# Or directly with psql
psql $DATABASE_URL -f database/data_retention_cleanup.sql
```

The cleanup script:
- Uses transactions for atomicity (all-or-nothing)
- Reports row counts and date ranges for each table
- Is safe to run multiple times (idempotent)
- Won't fail the workflow if errors occur

### Monitoring Retention

To check the age of your data:

```bash
# Check oldest and newest records in each layer
psql $DATABASE_URL -c "
SELECT 
  'raw_github_repos' as table_name,
  COUNT(*) as rows,
  MIN(fetch_timestamp) as oldest,
  MAX(fetch_timestamp) as newest
FROM raw_github_repos
UNION ALL
SELECT 
  'fact_repo_snapshots',
  COUNT(*),
  MIN(snapshot_date)::timestamptz,
  MAX(snapshot_date)::timestamptz
FROM fact_repo_snapshots;
"
```

### Adjusting Retention Windows

To modify retention periods, edit [`database/data_retention_cleanup.sql`](database/data_retention_cleanup.sql):

```sql
-- Change from 7 days to 14 days for raw layer
DELETE FROM raw_github_repos
WHERE fetch_timestamp < NOW() - INTERVAL '14 days';  -- was 7 days

-- Change from 30 days to 60 days for analytics
DELETE FROM fact_repo_snapshots
WHERE snapshot_date < CURRENT_DATE - INTERVAL '60 days';  -- was 30 days
```

### Troubleshooting

**Q: My dashboard only shows recent data**  
A: This is expected! The 30-day retention means the dashboard displays the last month of trending data, which aligns with platforms like GitHub Trending.

**Q: Can I temporarily disable cleanup?**  
A: Yes, comment out the cleanup call in `workflows/workflow.py` in the `aggregate_results()` function. Remember to re-enable it to prevent storage growth.

**Q: How do I recover deleted data?**  
A: Deleted data cannot be recovered. The raw layer is kept for 7 days specifically to allow reprocessing if needed before permanent deletion.

**Q: Cleanup failed - what should I do?**  
A: Check the workflow logs for errors. The cleanup is designed to fail gracefully without breaking the workflow. You can manually run the cleanup script once the issue is resolved.

## Success Metrics

**Technical:**
- Process 150 repos across 3 languages + Render ecosystem in 10-20 seconds
- 4x parallel task execution (Python, TypeScript, Go, Render)
- 3-layer data pipeline with dimensional modeling (9 tables + 6 views)
- Accurate Render discovery using code search (only root-level render.yaml files)

**Marketing:**
- Showcase trending Render ecosystem projects (render.yaml repositories)
- Highlight momentum scores combining stars and recency
- Identify case study candidates with high engagement
- Track Render service adoption patterns (web, worker, cron, etc.)

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
