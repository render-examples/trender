# Database

PostgreSQL schemas for the Trender analytics platform with a 3-layer data pipeline architecture.

## Overview

The database implements a **medallion architecture** (Raw → Staging → Analytics) with dimensional modeling for efficient querying and reporting.

## Architecture

```
Raw Layer (JSONB storage)
    ↓ Validation & Enrichment
Staging Layer (Cleaned data)
    ↓ Dimensional Modeling
Analytics Layer (Facts + Dimensions)
    ↓ Pre-aggregated Views
Dashboard Queries
```

## Schema files

| File | Purpose |
|------|---------|
| `init.sql` | Master initialization script (imports all schema files) |
| `schema/01_raw_layer.sql` | Raw data storage (GitHub API responses) |
| `schema/02_staging_layer.sql` | Validated & cleaned data |
| `schema/03_analytics_layer.sql` | Dimensional model (facts + dimensions) |
| `schema/04_views.sql` | Pre-aggregated analytics views |
| `schema/05_workflow_traces.sql` | Workflow execution tracking |

## Layer breakdown

### 1. Raw Layer (Retention: 7 days)

**Purpose**: Audit trail and reprocessing capability

**Tables:**

#### `raw_github_repos`
Stores complete GitHub API responses in JSONB format.

```sql
CREATE TABLE raw_github_repos (
    id BIGSERIAL PRIMARY KEY,
    repo_full_name VARCHAR(255) NOT NULL,
    api_response JSONB NOT NULL,
    fetch_timestamp TIMESTAMPTZ DEFAULT NOW(),
    source_language VARCHAR(50)  -- 'Python', 'TypeScript', 'Go', 'render'
);
```

**Use case**: Reprocess data without re-fetching from GitHub

#### `raw_repo_metrics`
Additional metrics fetched per repository.

```sql
CREATE TABLE raw_repo_metrics (
    id BIGSERIAL PRIMARY KEY,
    repo_full_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(50),
    metric_value JSONB,
    fetch_timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Staging Layer (Retention: 7 days)

**Purpose**: ETL audit trail and data quality validation

**Tables:**

#### `stg_repos_validated`
Cleaned and validated repository data ready for analytics.

```sql
CREATE TABLE stg_repos_validated (
    repo_full_name VARCHAR(255) PRIMARY KEY,
    repo_url VARCHAR(500),
    language VARCHAR(50) NOT NULL,
    description TEXT,
    stars INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    readme_content TEXT,
    loaded_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Business rules applied:**
- Non-null language
- Valid timestamps
- Star count ≥ 0

#### `stg_render_enrichment`
Render-specific metadata for repositories with `render.yaml`.

```sql
CREATE TABLE stg_render_enrichment (
    repo_full_name VARCHAR(255) PRIMARY KEY,
    render_category VARCHAR(50),
    render_services JSONB,  -- ['web', 'cron', 'worker', 'postgres', ...]
    render_complexity_score INTEGER,
    has_blueprint_button BOOLEAN,
    service_count INTEGER,
    loaded_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Enrichment logic:**
- Parse `render.yaml` to extract service types
- Calculate complexity score based on service count
- Categorize as 'official', 'community', or 'blueprint'

### 3. Analytics Layer (Retention: 30 days)

**Purpose**: Dimensional model for high-performance analytics

**Dimension tables:**

#### `dim_repositories`
Repository master data with SCD Type 2 history.

```sql
CREATE TABLE dim_repositories (
    repo_key BIGSERIAL PRIMARY KEY,
    repo_full_name VARCHAR(255) NOT NULL,
    repo_url VARCHAR(500),
    description TEXT,
    readme_content TEXT,
    language VARCHAR(50),
    created_at TIMESTAMPTZ,
    render_category VARCHAR(50),
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT TRUE
);
```

**SCD Type 2**: Tracks changes over time (description, README updates)

#### `dim_languages`
Language reference data.

```sql
CREATE TABLE dim_languages (
    language_key BIGSERIAL PRIMARY KEY,
    language_name VARCHAR(50) UNIQUE NOT NULL,
    language_category VARCHAR(50),
    display_name VARCHAR(100)
);
```

**Pre-populated values:**
- Python
- TypeScript
- Go
- render (for Render ecosystem repos)

#### `dim_render_services`
Render service type reference data.

```sql
CREATE TABLE dim_render_services (
    service_key BIGSERIAL PRIMARY KEY,
    service_type VARCHAR(50) UNIQUE NOT NULL,
    service_category VARCHAR(50),
    description TEXT
);
```

**Pre-populated values:**
- web, worker, cron, background-worker, private-service, static-site, postgres, redis

**Fact tables:**

#### `fact_repo_snapshots`
Daily snapshots of repository metrics and momentum scores.

```sql
CREATE TABLE fact_repo_snapshots (
    snapshot_key BIGSERIAL PRIMARY KEY,
    repo_key BIGINT REFERENCES dim_repositories(repo_key),
    language_key BIGINT REFERENCES dim_languages(language_key),
    snapshot_date DATE NOT NULL,
    stars INTEGER,
    star_velocity INTEGER,
    activity_score INTEGER,
    momentum_score NUMERIC(5, 3),
    rank_overall INTEGER,
    rank_in_language INTEGER
);
```

**Unique constraint**: `(repo_key, snapshot_date)`

#### `fact_render_usage`
Render service adoption by repository.

```sql
CREATE TABLE fact_render_usage (
    usage_key BIGSERIAL PRIMARY KEY,
    repo_key BIGINT REFERENCES dim_repositories(repo_key),
    service_key BIGINT REFERENCES dim_render_services(service_key),
    snapshot_date DATE NOT NULL,
    service_count INTEGER,
    complexity_score INTEGER,
    has_blueprint BOOLEAN
);
```

**Unique constraint**: `(repo_key, service_key, snapshot_date)`

#### `fact_workflow_runs`
Workflow execution traces for observability.

```sql
CREATE TABLE fact_workflow_runs (
    run_id VARCHAR(50) PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20),
    task_tree JSONB,
    error_message TEXT,
    repos_processed INTEGER,
    execution_time_seconds NUMERIC(10, 2)
);
```

### 4. Analytics views

Pre-aggregated views for dashboard queries.

#### `analytics_trending_repos_current`
Top trending repos across all languages.

```sql
SELECT 
    dr.repo_full_name,
    dr.language,
    frs.stars,
    frs.momentum_score,
    dr.description,
    dr.readme_content,
    dr.created_at
FROM fact_repo_snapshots frs
JOIN dim_repositories dr ON frs.repo_key = dr.repo_key
WHERE frs.snapshot_date = CURRENT_DATE
ORDER BY frs.momentum_score DESC
LIMIT 100;
```

#### `analytics_render_showcase`
Render ecosystem projects with enrichment.

```sql
SELECT 
    dr.repo_full_name,
    frs.stars,
    frs.momentum_score,
    fru.complexity_score,
    fru.has_blueprint,
    COUNT(DISTINCT fru.service_key) as service_count
FROM dim_repositories dr
JOIN fact_repo_snapshots frs ON dr.repo_key = frs.repo_key
LEFT JOIN fact_render_usage fru ON dr.repo_key = fru.repo_key
WHERE dr.language = 'render'
  AND frs.snapshot_date = CURRENT_DATE
GROUP BY 1, 2, 3, 4, 5
ORDER BY frs.momentum_score DESC;
```

#### `analytics_language_rankings`
Per-language leaderboards with Render adoption stats.

```sql
SELECT 
    dl.language_name,
    dr.repo_full_name,
    frs.stars,
    frs.momentum_score,
    frs.rank_in_language,
    EXISTS(SELECT 1 FROM fact_render_usage WHERE repo_key = dr.repo_key) as uses_render
FROM fact_repo_snapshots frs
JOIN dim_repositories dr ON frs.repo_key = dr.repo_key
JOIN dim_languages dl ON frs.language_key = dl.language_key
WHERE frs.snapshot_date = CURRENT_DATE
ORDER BY dl.language_name, frs.rank_in_language;
```

## Initialization

### Option 1: Setup script (recommended)

```bash
./bin/db_setup.sh
```

### Option 2: psql directly

```bash
cd database
psql $DATABASE_URL -f init.sql
```

### Option 3: Individual schema files

```bash
cd database
psql $DATABASE_URL -f schema/01_raw_layer.sql
psql $DATABASE_URL -f schema/02_staging_layer.sql
psql $DATABASE_URL -f schema/03_analytics_layer.sql
psql $DATABASE_URL -f schema/04_views.sql
psql $DATABASE_URL -f schema/05_workflow_traces.sql
```

### Verify

```bash
psql $DATABASE_URL -c "\dt"
psql $DATABASE_URL -c "\dv"
```

**Expected:**
- 9 tables
- 6+ views

## Maintenance scripts

### `data_retention_cleanup.sql`
Applies tiered retention policy (run automatically after each workflow).

**Retention windows:**
- Raw layer: 7 days
- Staging layer: 7 days
- Analytics layer: 30 days

**Manual run:**
```bash
psql $DATABASE_URL -f database/data_retention_cleanup.sql
```

### `cleanup_workflow_tracking.sql`
Migration script to remove old workflow execution tables (if upgrading).

```bash
psql $DATABASE_URL -f database/cleanup_workflow_tracking.sql
```

### `clear_data.sql`
**DESTRUCTIVE**: Truncates all tables (for testing only).

```bash
psql $DATABASE_URL -f database/clear_data.sql
```

### `check_analytics_load.sql`
Diagnostic query to verify data loading.

```bash
psql $DATABASE_URL -f database/check_analytics_load.sql
```

**Checks:**
- Row counts per table
- Latest snapshot dates
- Repository distribution by language

## Query utilities

### `row_counts.sql`
Get row counts for all tables.

```bash
psql $DATABASE_URL -f database/row_counts.sql
```

### `repos_by_language.sql`
Count repos per language.

```bash
psql $DATABASE_URL -f database/repos_by_language.sql
```

### `filter_vercel_repos.sql`
Example filtering query (customize as needed).

```bash
psql $DATABASE_URL -f database/filter_vercel_repos.sql
```

## Indexing strategy

**Key indexes for performance:**

```sql
-- Dimension lookups
CREATE INDEX idx_dim_repos_fullname ON dim_repositories(repo_full_name) WHERE is_current = TRUE;
CREATE INDEX idx_dim_languages_name ON dim_languages(language_name);

-- Fact table queries
CREATE INDEX idx_fact_snapshots_date ON fact_repo_snapshots(snapshot_date);
CREATE INDEX idx_fact_snapshots_momentum ON fact_repo_snapshots(momentum_score DESC);
CREATE INDEX idx_fact_render_usage_date ON fact_render_usage(snapshot_date);

-- Workflow traces
CREATE INDEX idx_workflow_runs_started ON fact_workflow_runs(started_at DESC);
```


## Data flow

```
GitHub API → workflows/workflow.py
    ↓ (store_raw_repos)
raw_github_repos
    ↓ (store_in_staging)
stg_repos_validated
stg_render_enrichment
    ↓ (load_to_analytics_simple)
dim_repositories
fact_repo_snapshots
fact_render_usage
    ↓ (views)
analytics_trending_repos_current
analytics_render_showcase
    ↓ (queries)
dashboard/lib/db.ts
    ↓
Next.js components
```

## Contributing

1. Add new schema files to `schema/`
2. Update `init.sql` to import new files
3. Document tables in this README
4. Test with `./bin/db_setup.sh`
5. Add indexes for frequently queried columns

