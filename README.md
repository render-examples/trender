# [trender.onrender.com](https://trender.onrender.com/)

A distributed analytics platform that tracks trending GitHub repositories across Python, TypeScript/Next.js, Go, and the Render ecosystem. Uses Render Workflows for parallel processing and a 3-layer data pipeline (Raw → Staging → Analytics) for high-performance analytics.

## Demo

https://github.com/user-attachments/assets/ba79db68-fc73-4508-9d90-0f4abcf050a7

## 🎯 Quick start

```bash
# 1. Clone and setup
git clone https://github.com/render-examples/trender.git
cd trender
cp .env.example .env

# 2. Get GitHub token (required for API access)
cd workflows
pip install -r requirements.txt
python auth_setup.py  # Follow prompts to get GITHUB_ACCESS_TOKEN

# 3. Create Render PostgreSQL database
# Visit dashboard.render.com → New PostgreSQL
# Add DATABASE_URL to .env

# 4. Initialize database
./bin/db_setup.sh

# 5. Deploy to Render
# Push to GitHub, then: Dashboard → New Blueprint → Connect repo
# Or: render blueprint launch

# 6. Create Render API key
# Visit dashboard.render.com → Account Settings → API Keys → Create API Key
# Copy the key for next step

# 7. Trigger first run
cd trigger
pip install -r requirements.txt
export RENDER_API_KEY=<your_key>
export RENDER_WORKFLOW_SLUG=trender-wf
python trigger.py
```

## 🏗️ Architecture

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

**Data pipeline:**
- **Raw layer**: Complete GitHub API responses (JSONB) - 7 day retention
- **Staging layer**: Validated & cleaned data with business rules - 7 day retention
- **Analytics layer**: Dimensional model (facts + dimensions) - 30 day retention

**Processing:**
- 4 parallel workflow tasks (Python, TypeScript, Go, Render)
- ~150 repos analyzed in 10-20 seconds
- Automated hourly updates via cron

## 📁 Project structure

```
trender/
├── workflows/          # Python workflows (ETL pipeline)
├── dashboard/          # Next.js dashboard (UI)
├── database/           # PostgreSQL schemas & migrations
├── trigger/            # Cron trigger script
├── bin/               # Utility scripts
├── render-mcp-server/ # MCP server for Render API
└── render.yaml        # Render service configuration
```

See individual README files in each directory for details.

## 🔧 Tech stack

**Backend:**
- Python 3.11+ with Render Workflows SDK
- asyncpg for PostgreSQL
- aiohttp for async GitHub API calls

**Frontend:**
- Next.js 14.2 (App Router)
- TypeScript, Tailwind CSS
- Recharts for visualizations

**Infrastructure:**
- Render Workflows (distributed task execution)
- Render Cron Job (hourly trigger)
- Render Web Service (dashboard)
- Render PostgreSQL (data storage)

## 📊 Key features

- **Multi-language analysis**: Python, TypeScript, Go, and Render ecosystem
- **Parallel processing**: 4 concurrent tasks using Workflows SDK
- **Momentum scoring**: 70% recency + 30% stars to surface emerging projects
- **Automated retention**: Tiered cleanup (7/7/30 days) to control storage costs
- **Real-time dashboard**: Live analytics with historical trends

## 🚀 Development

### Local workflow testing

```bash
# Quick start (server + trigger in one command)
python bin/local_dev.py

# Or manual:
cd workflows
python workflow.py  # Starts task server on port 8120
# In another terminal:
cd trigger
python trigger.py
```

### Local dashboard

```bash
cd dashboard
npm install
npm run dev
# Visit http://localhost:3000
```

## 📖 Documentation

- **[Setup Guide](database/schema/)** - Database initialization details
- **[Workflows README](workflows/README.md)** - ETL pipeline & task orchestration
- **[Dashboard README](dashboard/README.md)** - Frontend architecture
- **[Database README](database/README.md)** - Schema & data model
- **[Bin Scripts](bin/README.md)** - Utility scripts reference

## 🔐 Authentication

Trender supports two GitHub auth methods:

**Option A: Personal access token (PAT)** - Recommended for individual use
1. Run `python workflows/auth_setup.py`
2. Choose option [1]
3. Follow prompts to create token at github.com/settings/tokens/new
4. Required scopes: `repo`, `read:org`

**Option B: OAuth app** - For team setups
1. Create OAuth app at github.com/settings/developers
2. Add `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` to `.env`
3. Run `python workflows/auth_setup.py` and choose option [2]

Both methods output a `GITHUB_ACCESS_TOKEN` for `.env`.

## 🎯 Metrics and scoring

**Momentum score formula:**
- 70% Recency (exponential decay favoring repos ≤14 days old)
- 30% Normalized stars (separate normalization for general vs Render repos)

**Render detection:**
- Code search for `render.yaml` in repository root
- Repositories assigned `language='render'` for clean identification
- Service complexity scoring based on service count and types

## 🗄️ Data retention

Automatic cleanup after each workflow run:

| Layer | Retention | Purpose |
|-------|-----------|---------|
| Raw | 7 days | Debugging & reprocessing |
| Staging | 7 days | ETL audit trail |
| Analytics | 30 days | Dashboard trending data |

Manual cleanup: `./bin/cleanup_data.sh`

## 📦 Deployment

The `render.yaml` defines all services:
- **trender-dashboard**: Next.js web service
- **trender-wf**: Workflow orchestrator
- **trender-cron**: Hourly trigger (6 AM PST / 14:00 UTC)
- **trender-db**: PostgreSQL database

Deploy via Render Dashboard (Blueprint) or CLI:
```bash
render blueprint launch
```

**Post-deployment:**
1. Add `GITHUB_ACCESS_TOKEN` to workflow environment variables
2. Trigger manual deploy to apply env vars
3. Test with `python trigger/trigger.py`

## 📄 License

MIT

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.
