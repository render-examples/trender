# Trender: GitHub Trending Analytics Platform

A batch analytics platform with a **3-layer data engineering pipeline** (Raw → Staging → Analytics) that analyzes trending GitHub repositories across 3 programming languages (Python, TypeScript with Next.js >= 16, and Go). Leverages Render Workflows' distributed task execution to process data in parallel, storing results in a dimensional model for high-performance analytics.

## Key Features

- **Multi-Language Analysis**: Tracks Python, TypeScript/Next.js, and Go repositories
- **3-Layer Data Pipeline**: Raw ingestion → Staging validation → Analytics dimensional model
- **Parallel Processing**: 4 concurrent workflow tasks using Render Workflows SDK
- **Render Ecosystem Spotlight**: Dedicated showcase for Render-deployed projects
- **Real-time Dashboard**: Next.js 14 dashboard with analytics visualizations
- **Hourly Updates**: Automated cron job triggers workflow execution

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
- Next.js 14 (App Router)
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
│   ├── metrics.py            # Momentum/activity calculations
│   ├── render_detection.py  # Render usage detection
│   ├── etl/
│   │   ├── extract.py        # Raw layer extraction
│   │   ├── transform.py      # Staging transformations
│   │   ├── load.py           # Analytics layer loading
│   │   └── data_quality.py   # Quality scoring
│   └── requirements.txt
├── trigger/
│   ├── trigger.py            # Cron trigger script
│   └── requirements.txt
├── dashboard/
│   ├── app/                  # Next.js App Router pages
│   ├── lib/
│   │   └── db.ts            # Database utilities
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

- GitHub OAuth App (we'll create this in step 2)
- Render account
- Node.js 18+ (for dashboard)
- Python 3.11+ (for workflows)

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd trender
```

### 2. One-Time GitHub OAuth Setup

This is a **one-time setup** that creates a long-lived GitHub access token for the workflow to use. You'll need to complete this before deploying to Render.

#### Step 2.1: Create GitHub OAuth App

1. Go to https://github.com/settings/developers
2. Click **"New OAuth App"**
3. Fill in the details:
   - **Application name**: `Trender Analytics` (or your choice)
   - **Homepage URL**: Your repository URL or `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:8000/callback`
4. Click **"Register application"**
5. Note your **Client ID** (starts with `Iv1.`)
6. Click **"Generate a new client secret"** and save it securely

**Important Notes:**
- The callback URL `http://localhost:8000/callback` is required for the authorization flow
- Keep your Client Secret secure - you'll need it for the next step
- This OAuth app allows Trender to access GitHub's API on your behalf

#### Step 2.2: Add OAuth Credentials to .env

Add your GitHub OAuth credentials to `.env`:

```bash
GITHUB_CLIENT_ID=Iv1.your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
```

#### Step 2.3: Generate Access Token

Run the OAuth setup script to generate your access token:

```bash
cd workflows
pip install -r requirements.txt
python oauth_setup.py
```

**What happens during authorization:**
1. A local server starts on `http://localhost:8000`
2. Your browser automatically opens to GitHub's authorization page
3. Review the requested permissions:
   - **`repo`**: Read repository data (stars, forks, commits)
   - **`read:org`**: Read organization membership (for Render ecosystem detection)
4. Click **"Authorize"** to approve the application
5. You'll be redirected to `http://localhost:8000/callback`
6. The script exchanges the authorization code for an access token
7. Your access token is displayed in the terminal

**Example output:**
```
=== GitHub OAuth App Setup ===

1. Starting local callback server on port 8000...
2. Opening browser for authorization...
3. Waiting for authorization callback...
4. Authorization code received!
5. Exchanging code for access token...

============================================================
✓ SUCCESS! Your GitHub OAuth access token:
============================================================

ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

============================================================
Add this to your .env file and Render Dashboard:
GITHUB_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
============================================================
```

#### Step 2.4: Save Your Access Token

1. **Copy the token** from the terminal output
2. Add it to your `.env` file:
   ```bash
   GITHUB_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. **Store it securely** - you'll need to add this to Render's environment variables later (step 8)

**Security Best Practices:**
- ✅ This token does **not expire** - you only generate it once
- ✅ Never commit the token to version control (`.env` is in `.gitignore`)
- ✅ The token has limited scopes (`repo` and `read:org` only)
- ✅ You can revoke access anytime at https://github.com/settings/applications
- ⚠️  Treat this token like a password

#### Troubleshooting OAuth Setup

**Problem: Browser doesn't open automatically**
- Manually navigate to the URL shown in the terminal
- The URL will look like: `https://github.com/login/oauth/authorize?client_id=...`

**Problem: Port 8000 is already in use**
```bash
# Find and kill the process using port 8000
lsof -ti:8000 | xargs kill -9
# Then run oauth_setup.py again
```

**Problem: "Bad verification code" error**
- The authorization code can only be used once
- Run `python oauth_setup.py` again to get a new code
- Complete the authorization within 10 minutes

**Problem: Need to regenerate token**
- Go to https://github.com/settings/tokens
- Find and revoke the old token
- Run `python oauth_setup.py` again to generate a new one

**Problem: "Access denied" when authorizing**
- Ensure you have admin access to your GitHub account
- Try signing out of GitHub and back in
- Clear your browser cookies for github.com

### 3. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

Your `.env` file should now contain (from step 2):
```bash
GITHUB_CLIENT_ID=Iv1.your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
GITHUB_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Other required variables (add as you complete the setup):
- `DATABASE_URL`: PostgreSQL connection string (from step 4)
- `RENDER_API_KEY`: Render API key (from https://dashboard.render.com/u/settings#api-keys)
- `RENDER_WORKFLOW_SLUG`: `trender-wf` (or your workflow slug from step 6)

### 4. Create PostgreSQL Database on Render

1. Go to Render Dashboard
2. Create new PostgreSQL database named `trender`
3. Note the connection string for `DATABASE_URL`

### 5. Initialize Database Schema

#### Option 1: Using the init.sql script (Recommended)

```bash
# Connect to your Render PostgreSQL instance and run the initialization script

DATABASE_URL=YOUR_DATABASE_URL
psql $DATABASE_URL -f database/init.sql
```

#### Option 2: Run schema files individually

If you prefer to run the schema files one at a time:

```bash
# Run each schema file in order
psql $DATABASE_URL -f database/schema/01_raw_layer.sql
psql $DATABASE_URL -f database/schema/02_staging_layer.sql
psql $DATABASE_URL -f database/schema/03_analytics_layer.sql
psql $DATABASE_URL -f database/schema/04_views.sql
```

#### What gets created:

**Raw Layer:**
- `raw_github_repos`: Stores complete GitHub API responses
- `raw_repo_metrics`: Stores repository metrics (stars, forks, issues)

**Staging Layer:**
- `stg_repos_validated`: Cleaned and validated repository data
- `stg_render_enrichment`: Render-specific metadata and detection

**Analytics Layer:**
- Dimension tables: `dim_repositories`, `dim_languages`, `dim_render_services`
- Fact tables: `fact_repo_snapshots`, `fact_render_usage`, `fact_workflow_executions`

**Views:**
- Pre-aggregated analytics views for dashboard queries

#### Verify Database Initialization

Check that all tables were created successfully:

```bash
psql $DATABASE_URL -c "\dt"
```

You should see 12+ tables across the raw, stg, dim, and fact prefixes.

#### Troubleshooting

- **Connection refused**: Ensure your `DATABASE_URL` is correct and the Render PostgreSQL instance is active
- **Permission denied**: Make sure you're using the connection string with full admin privileges
- **Tables already exist**: Drop the database and recreate it, or use `DROP TABLE IF EXISTS` statements

### 6. Deploy Services via render.yaml

The `render.yaml` file defines:
- **Web Service**: Next.js dashboard
- **Cron Job**: Hourly workflow trigger
- **Database**: PostgreSQL instance

Deploy to Render:
```bash
# Push to GitHub and connect to Render
# Or use Render Blueprint button
```

### 7. Configure Environment Variables in Render

After deploying via `render.yaml`, add the following environment variables to your **workflow service** (`trender-wf`) in the Render Dashboard:

1. Go to your `trender-wf` workflow
2. Navigate to **Environment** tab
3. Add:
   - `GITHUB_ACCESS_TOKEN`: The token from step 2
   - `DATABASE_URL`: Automatically connected from the database

**Important:** After adding these variables, trigger a manual deploy:
- Click **"Manual Deploy"** → **"Clear build cache & deploy"**
- This ensures the environment variables are available to your workflow tasks

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
export RENDER_WORKFLOW_SLUG=trender  # Your workflow slug from Render dashboard

# Run the trigger script
python trigger.py
```

Expected output:
```
Triggering task: trender/main-analysis-task
✓ Workflow triggered successfully at 2026-01-20 12:00:00
  Task Run ID: run_abc123xyz
  Initial Status: running
```

#### Method 2: Using the Render Dashboard

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Navigate to **Workflows** section
3. Select your `trender` workflow
4. Click **"Trigger Workflow"** button
5. Select the `main-analysis-task` task
6. Click **"Run Task"**

#### Method 3: Using Render CLI

If you have the Render CLI installed:

```bash
# Install Render CLI (if not already installed)
npm install -g @render-inc/cli

# Login to Render
render login

# Trigger the workflow
render workflows trigger trender main-analysis-task
```

#### Verify Workflow Execution

Check the workflow status:

1. **Via Dashboard**: Go to Workflows → trender → View recent runs
2. **Via Script**: The trigger script outputs the Task Run ID
3. **Via Database**: Query the `fact_workflow_executions` table:

```bash
psql $DATABASE_URL -c "SELECT * FROM fact_workflow_executions ORDER BY execution_date DESC LIMIT 1;"
```

Expected workflow completion time: **8-15 seconds** for ~300 repositories

#### Troubleshooting

- **"RENDER_API_KEY not set"**: Export your API key from [Render Settings](https://dashboard.render.com/u/settings#api-keys)
- **"Task not found"**: Verify your workflow slug and that the workflow is deployed
- **"Connection refused"**: Check that `DATABASE_URL` is correct and the database is running
- **Workflow fails**: Check the Render dashboard logs for detailed error messages

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
- Data quality scoring (0.0 - 1.0)
- Business rules applied

### Layer 3: Analytics (Dimensional Model)
- **Dimensions**: `dim_repositories`, `dim_languages`, `dim_render_services`
- **Facts**: `fact_repo_snapshots`, `fact_render_usage`, `fact_workflow_executions`
- **Views**: Pre-aggregated analytics for dashboard

## Workflow Tasks

The workflow consists of 8 tasks decorated with `@task`:

1. **`main_analysis_task`**: Orchestrator that spawns parallel tasks
2. **`fetch_language_repos`**: Fetches repos for Python, TypeScript, Go
3. **`analyze_repo_batch`**: Analyzes repos in batches of 10
4. **`fetch_render_ecosystem`**: Fetches Render-related projects
5. **`analyze_render_projects`**: Analyzes Render-specific features
6. **`aggregate_results`**: ETL pipeline execution (Extract → Transform → Load)
7. **`store_execution_stats`**: Records workflow performance metrics

## Metrics Calculated

- **Star Velocity**: `(stars_last_7_days / total_stars) * 100`
- **Activity Score**: Weighted formula using commits, issues, contributors
- **Momentum Score**: `(star_velocity * 0.4) + (activity_score * 0.6)`
- **Render Boost**: 1.2x multiplier for projects using Render
- **Freshness Penalty**: 0.9x for repos older than 180 days

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

```bash
psql $DATABASE_URL -f database/schema/01_raw_layer.sql
psql $DATABASE_URL -f database/schema/02_staging_layer.sql
psql $DATABASE_URL -f database/schema/03_analytics_layer.sql
psql $DATABASE_URL -f database/schema/04_views.sql
```

## Success Metrics

**Technical:**
- Process 300+ repos across 3 languages in under 10 seconds
- 3x speedup vs sequential processing
- 99%+ success rate on workflow runs
- Data quality score >= 0.90 for 95%+ repositories

**Marketing:**
- Showcase 50+ Render ecosystem projects
- Track Render adoption vs competitors
- Identify case study candidates

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
