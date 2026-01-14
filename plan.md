# Trender: GitHub Trending Analytics Platform

## Project Overview

A batch analytics platform with a **3-layer data engineering pipeline** (Raw → Staging → Analytics) that analyzes trending GitHub repositories across 3 programming languages (Python, TypeScript with Next.js >= 16, and Go). Leverages Render Workflows' distributed task execution to process data in parallel, storing results in a dimensional model for high-performance analytics. Runs hourly via cron to update trending metrics and specially highlights Render's open-source ecosystem.

**Key Value Propositions:**

- **For Developers**: Discover emerging tools before they hit mainstream across Python, TypeScript/Next.js, and Go ecosystems
- **For Render Workflows**: Showcase parallel execution (4 parallel streams), sub-second spin-up, retries, and API integration patterns with ETL pipeline
- **For Render Marketing**: Built-in spotlight on Render OSS projects, employee work, and community success stories with data-driven insights
- **For Data Engineering**: Demonstrates production-grade layered data architecture with fact/dimension modeling and SCD Type 2

## Architecture

```mermaid
graph TD
    Cron[Cron Job Hourly] --> MainTask[@task main_analysis_task]
    MainTask --> |asyncio.gather| LangPython[@task fetch_language_repos python]
    MainTask --> |asyncio.gather| LangTS[@task fetch_language_repos typescript]
    MainTask --> |asyncio.gather| LangGo[@task fetch_language_repos go]
    MainTask --> |asyncio.gather| RenderEco[@task fetch_render_ecosystem]
    
    LangPython --> AnalyzeBatch1[@task analyze_repo_batch]
    LangTS --> AnalyzeBatch2[@task analyze_repo_batch]
    LangGo --> AnalyzeBatch3[@task analyze_repo_batch]
    
    AnalyzeBatch1 --> CalcMetrics1[@task calculate_metrics]
    AnalyzeBatch2 --> CalcMetrics2[@task calculate_metrics]
    AnalyzeBatch3 --> CalcMetrics3[@task calculate_metrics]
    
    RenderEco --> AnalyzeRender[@task analyze_render_projects]
    AnalyzeRender --> DetectUsage[@task detect_render_usage]
    
    CalcMetrics1 --> RawLayer[Raw Layer - raw_github_repos]
    CalcMetrics2 --> RawLayer
    CalcMetrics3 --> RawLayer
    DetectUsage --> RawLayer
    
    RawLayer --> StagingLayer[Staging Layer - stg_repos_validated]
    StagingLayer --> AnalyticsLayer[Analytics Layer - Fact/Dim Tables]
    
    AnalyticsLayer --> Dashboard[Next.js Dashboard]
    
    style MainTask fill:#ff6b6b
    style LangPython fill:#4ecdc4
    style LangTS fill:#4ecdc4
    style LangGo fill:#4ecdc4
    style RenderEco fill:#4ecdc4
```

**All workflow tasks use `@task` decorator from Render Workflows SDK and execute asynchronously with shared resources (github_api, db_pool).**

### Data Pipeline Layers

**Raw Layer**: Unprocessed GitHub API responses
**Staging Layer**: Cleaned, validated, and enriched data
**Analytics Layer**: Aggregated metrics with fact/dimension model

### Data Flow

1. **Ingestion (Raw Layer)**
   - GitHub API responses → `raw_github_repos` (full JSON payload)
   - Detailed metrics API calls → `raw_repo_metrics` (commits, issues, contributors)
   - Preserves complete source data for auditing and reprocessing

2. **Transformation (Staging Layer)**
   - Parse and validate raw JSON → `stg_repos_validated`
   - Calculate data quality scores (completeness, freshness)
   - Enrich with Render detection → `stg_render_enrichment`
   - Apply business rules and data cleaning

3. **Analytics (Dimensional Model)**
   - Upsert repositories → `dim_repositories` (SCD Type 2)
   - Daily metrics snapshot → `fact_repo_snapshots`
   - Render usage facts → `fact_render_usage`
   - Workflow execution facts → `fact_workflow_executions`
   - Pre-aggregated views for dashboard queries

**Benefits of Layered Architecture:**
- **Reprocessability**: Can reprocess raw data with updated business logic
- **Data Quality Tracking**: Quality scores at staging layer
- **Historical Analysis**: SCD Type 2 tracks repository changes over time
- **Query Performance**: Analytics views optimized for dashboard
- **Separation of Concerns**: ETL logic clearly separated by layer

## Tech Stack

**Backend (Workflows)**

- Python 3.11+
- Render Workflows SDK
- GitHub API (REST)
- PostgreSQL client (asyncpg)
- aiohttp for async API calls

**Frontend (Dashboard)**

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Recharts for visualizations
- PostgreSQL connection (pg)

**Infrastructure**

- Render Workflows (task execution)
- Render Cron Job (hourly trigger)
- Render Web Service (Next.js dashboard)
- Render PostgreSQL (data storage)

## Implementation Phases

### Phase 1: Database and Schema Setup - Data Engineering Pipeline

Create PostgreSQL database with **3-layer architecture** (Raw → Staging → Analytics):

#### Raw Layer - Ingestion Tables

**`raw_github_repos`** - Unprocessed GitHub API responses

```sql
CREATE TABLE raw_github_repos (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) NOT NULL,
  api_response JSONB NOT NULL,
  fetch_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  source_language VARCHAR(50),
  source_type VARCHAR(20) -- 'trending', 'render_ecosystem'
);
CREATE INDEX idx_raw_repos_fetch ON raw_github_repos(fetch_timestamp);
CREATE INDEX idx_raw_repos_name ON raw_github_repos(repo_full_name);
```

**`raw_repo_metrics`** - Raw GitHub metrics (commits, issues, contributors)

```sql
CREATE TABLE raw_repo_metrics (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) NOT NULL,
  metric_type VARCHAR(50) NOT NULL, -- 'commits', 'issues', 'contributors'
  metric_data JSONB NOT NULL,
  fetch_timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_raw_metrics_repo ON raw_repo_metrics(repo_full_name, fetch_timestamp);
```

#### Staging Layer - Validated and Enriched

**`stg_repos_validated`** - Cleaned and validated repository data

```sql
CREATE TABLE stg_repos_validated (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) UNIQUE NOT NULL,
  repo_url TEXT NOT NULL,
  language VARCHAR(50) NOT NULL,
  description TEXT,
  stars INTEGER NOT NULL,
  forks INTEGER,
  open_issues INTEGER,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  commits_last_7_days INTEGER DEFAULT 0,
  issues_closed_last_7_days INTEGER DEFAULT 0,
  active_contributors INTEGER DEFAULT 0,
  uses_render BOOLEAN DEFAULT FALSE,
  render_yaml_content TEXT,
  readme_content TEXT,
  data_quality_score DECIMAL(3,2), -- 0.00 to 1.00
  loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT valid_stars CHECK (stars >= 0),
  CONSTRAINT valid_quality CHECK (data_quality_score BETWEEN 0 AND 1)
);
CREATE INDEX idx_stg_repos_language ON stg_repos_validated(language);
CREATE INDEX idx_stg_repos_updated ON stg_repos_validated(updated_at);
```

**`stg_render_enrichment`** - Render-specific enrichment data

```sql
CREATE TABLE stg_render_enrichment (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) UNIQUE NOT NULL REFERENCES stg_repos_validated(repo_full_name),
  render_category VARCHAR(50), -- 'official', 'employee', 'community', 'blueprint'
  render_services TEXT[],
  has_blueprint_button BOOLEAN DEFAULT FALSE,
  render_complexity_score INTEGER CHECK (render_complexity_score BETWEEN 0 AND 10),
  deploy_button_url TEXT,
  service_count INTEGER,
  loaded_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### Analytics Layer - Dimensional Model

**Dimension Tables:**

**`dim_repositories`** - Repository dimension (SCD Type 2)

```sql
CREATE TABLE dim_repositories (
  repo_key SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) NOT NULL,
  repo_url TEXT NOT NULL,
  description TEXT,
  language VARCHAR(50) NOT NULL,
  created_at TIMESTAMP NOT NULL,
  uses_render BOOLEAN DEFAULT FALSE,
  render_category VARCHAR(50),
  valid_from TIMESTAMP NOT NULL DEFAULT NOW(),
  valid_to TIMESTAMP,
  is_current BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_dim_repos_name_current ON dim_repositories(repo_full_name, is_current);
CREATE INDEX idx_dim_repos_language ON dim_repositories(language);
```

**`dim_languages`** - Language dimension

```sql
CREATE TABLE dim_languages (
  language_key SERIAL PRIMARY KEY,
  language_name VARCHAR(50) UNIQUE NOT NULL,
  language_category VARCHAR(50), -- 'general', 'web', 'systems', etc.
  ecosystem_size VARCHAR(20) -- 'small', 'medium', 'large'
);
INSERT INTO dim_languages (language_name, language_category, ecosystem_size) VALUES
  ('Python', 'general', 'large'),
  ('TypeScript', 'web', 'large'),
  ('Go', 'systems', 'large');
```

**`dim_render_services`** - Render service types dimension

```sql
CREATE TABLE dim_render_services (
  service_key SERIAL PRIMARY KEY,
  service_type VARCHAR(50) UNIQUE NOT NULL, -- 'web', 'worker', 'cron', 'private', etc.
  service_description TEXT
);
```

**Fact Tables:**

**`fact_repo_snapshots`** - Time-series metrics (daily snapshots)

```sql
CREATE TABLE fact_repo_snapshots (
  snapshot_id SERIAL PRIMARY KEY,
  repo_key INTEGER NOT NULL REFERENCES dim_repositories(repo_key),
  language_key INTEGER NOT NULL REFERENCES dim_languages(language_key),
  snapshot_date DATE NOT NULL,
  stars INTEGER NOT NULL,
  forks INTEGER,
  star_velocity DECIMAL(7,2), -- stars gained per day
  activity_score DECIMAL(7,2),
  momentum_score DECIMAL(7,2),
  commits_last_7_days INTEGER,
  issues_closed_last_7_days INTEGER,
  active_contributors INTEGER,
  rank_overall INTEGER,
  rank_in_language INTEGER,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(repo_key, snapshot_date)
);
CREATE INDEX idx_fact_snapshots_date ON fact_repo_snapshots(snapshot_date);
CREATE INDEX idx_fact_snapshots_momentum ON fact_repo_snapshots(momentum_score DESC);
```

**`fact_render_usage`** - Render service usage facts

```sql
CREATE TABLE fact_render_usage (
  usage_id SERIAL PRIMARY KEY,
  repo_key INTEGER NOT NULL REFERENCES dim_repositories(repo_key),
  service_key INTEGER NOT NULL REFERENCES dim_render_services(service_key),
  snapshot_date DATE NOT NULL,
  service_count INTEGER DEFAULT 1,
  complexity_score INTEGER,
  has_blueprint BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_fact_render_repo ON fact_render_usage(repo_key, snapshot_date);
```

**`fact_workflow_executions`** - Workflow performance metrics

```sql
CREATE TABLE fact_workflow_executions (
  execution_id SERIAL PRIMARY KEY,
  execution_date TIMESTAMP NOT NULL DEFAULT NOW(),
  total_duration_seconds DECIMAL(8,2),
  repos_processed INTEGER,
  tasks_executed INTEGER,
  tasks_succeeded INTEGER,
  tasks_failed INTEGER,
  tasks_retried INTEGER,
  parallel_speedup_factor DECIMAL(5,2), -- vs sequential
  languages_processed TEXT[],
  error_details JSONB,
  success_rate DECIMAL(5,2)
);
CREATE INDEX idx_fact_executions_date ON fact_workflow_executions(execution_date);
```

#### Aggregated Analytics Views

**`analytics_trending_repos_current`** - Current top trending repositories

```sql
CREATE VIEW analytics_trending_repos_current AS
SELECT 
  dr.repo_full_name,
  dr.repo_url,
  dr.language,
  dr.description,
  dr.uses_render,
  dr.render_category,
  fs.stars,
  fs.star_velocity,
  fs.activity_score,
  fs.momentum_score,
  fs.rank_overall,
  fs.rank_in_language,
  fs.commits_last_7_days,
  fs.active_contributors,
  fs.snapshot_date
FROM dim_repositories dr
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE dr.is_current = TRUE
  AND fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
ORDER BY fs.momentum_score DESC;
```

**`analytics_render_showcase`** - Render ecosystem showcase

```sql
CREATE VIEW analytics_render_showcase AS
SELECT 
  dr.repo_full_name,
  dr.repo_url,
  dr.language,
  dr.render_category,
  fs.stars,
  fs.momentum_score,
  sre.render_services,
  sre.service_count,
  sre.render_complexity_score,
  sre.has_blueprint_button,
  fs.snapshot_date
FROM dim_repositories dr
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
LEFT JOIN stg_render_enrichment sre ON dr.repo_full_name = sre.repo_full_name
WHERE dr.is_current = TRUE
  AND dr.uses_render = TRUE
  AND fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
ORDER BY fs.momentum_score DESC;
```

**`analytics_language_rankings`** - Per-language top performers

```sql
CREATE VIEW analytics_language_rankings AS
SELECT 
  dl.language_name,
  dr.repo_full_name,
  fs.stars,
  fs.momentum_score,
  fs.rank_in_language,
  fs.snapshot_date,
  COUNT(CASE WHEN dr.uses_render THEN 1 END) OVER (PARTITION BY dl.language_name) as render_adoption_count
FROM dim_languages dl
JOIN dim_repositories dr ON dl.language_name = dr.language
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE dr.is_current = TRUE
  AND fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
  AND fs.rank_in_language <= 50
ORDER BY dl.language_name, fs.rank_in_language;
```

### Phase 2: GitHub API Integration Layer

Create Python module `github_api.py` with async GitHub API client:

```python
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

class GitHubAPIClient:
    """Async GitHub API client with rate limiting and retry logic."""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        })
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def _api_call(self, url: str) -> dict:
        """Make API call with rate limiting."""
        # Check rate limit
        if self.rate_limit_remaining < 100:
            if self.rate_limit_reset:
                sleep_duration = max(self.rate_limit_reset - datetime.utcnow().timestamp(), 0)
                await asyncio.sleep(sleep_duration + 5)
        
        async with self.session.get(url) as response:
            # Update rate limit info
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
            self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
            
            response.raise_for_status()
            return await response.json()
    
    async def search_repositories(self, language: str, sort: str = 'stars', 
                                 updated_since: datetime = None) -> List[Dict]:
        """Search repositories by language."""
        query = f"language:{language}"
        if updated_since:
            query += f" pushed:>={updated_since.strftime('%Y-%m-%d')}"
        
        url = f"{self.base_url}/search/repositories?q={query}&sort={sort}&per_page=100"
        result = await self._api_call(url)
        return result.get('items', [])
    
    async def get_repo_details(self, owner: str, repo: str) -> Dict:
        """Get detailed repository information."""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        return await self._api_call(url)
    
    async def get_commits(self, owner: str, repo: str, since: datetime) -> List[Dict]:
        """Get commits since a specific date."""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits?since={since.isoformat()}"
        return await self._api_call(url)
    
    async def get_issues(self, owner: str, repo: str, state: str = 'closed', 
                        since: datetime = None) -> List[Dict]:
        """Get issues for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues?state={state}"
        if since:
            url += f"&since={since.isoformat()}"
        return await self._api_call(url)
    
    async def get_contributors(self, owner: str, repo: str) -> List[Dict]:
        """Get repository contributors."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contributors"
        return await self._api_call(url)
    
    async def get_file_contents(self, owner: str, repo: str, path: str) -> Optional[str]:
        """Get file contents from repository."""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            result = await self._api_call(url)
            import base64
            return base64.b64decode(result['content']).decode('utf-8')
        except Exception:
            return None
    
    async def search_by_topic(self, topic: str) -> List[Dict]:
        """Search repositories by topic."""
        url = f"{self.base_url}/search/repositories?q=topic:{topic}&per_page=100"
        result = await self._api_call(url)
        return result.get('items', [])
    
    async def search_readme_mentions(self, keyword: str) -> List[Dict]:
        """Search for keyword mentions in README files."""
        url = f"{self.base_url}/search/code?q={keyword}+in:readme&per_page=100"
        result = await self._api_call(url)
        return result.get('items', [])
    
    async def get_org_repos(self, org: str) -> List[Dict]:
        """Get all repositories for an organization."""
        url = f"{self.base_url}/orgs/{org}/repos?per_page=100"
        return await self._api_call(url)
```

**Key Features:**
- **Async/await pattern** throughout for non-blocking I/O
- **Rate limit handling** with automatic backoff (preserves 100 request buffer)
- **Session management** with context manager support
- **Exponential backoff** on rate limit exceeded
- **Automatic token injection** in headers
- **Error handling** with graceful degradation

**Environment Variables - `.env.example`:**

```bash
# GitHub API
GITHUB_TOKEN=ghp_your_personal_access_token_here
GITHUB_API_BASE_URL=https://api.github.com

# Database
DATABASE_URL=postgresql://user:password@host:5432/trender
DATABASE_POOL_SIZE=10

# Render Workflows
RENDER_WORKFLOW_ID=your_workflow_id
RENDER_API_KEY=rnd_your_api_key

# Render Cron (for trigger service)
WORKFLOW_TRIGGER_URL=https://api.render.com/v1/workflows/{workflow_id}/trigger

# Next.js Dashboard
NEXT_PUBLIC_API_URL=https://trender-dashboard.onrender.com
NEXT_PUBLIC_ENABLE_DEBUG=false

# Optional: Render Ecosystem Detection
RENDER_EMPLOYEE_GITHUB_ORGS=render-examples,render
RENDER_OFFICIAL_TOPICS=render,render-deploy,render-blueprints
```

### Phase 3: Render Workflows Task Implementation

Create `workflow.py` with 8 interconnected tasks using Render Workflows SDK:

**Task 1: `main_analysis_task()`** (Orchestrator)

```python
from render_sdk.workflows import task
import asyncio

TARGET_LANGUAGES = ['Python', 'TypeScript', 'Go']

@task
async def main_analysis_task() -> Dict:
    """Orchestrates the entire analysis workflow."""
    # Initialize shared resources
    github_api, db_pool = await init_connections()
    execution_start = datetime.utcnow()
    
    try:
        # Spawn parallel language analysis tasks
        language_tasks = [
            fetch_language_repos(lang, github_api, db_pool)
            for lang in TARGET_LANGUAGES
        ]
        
        # Execute language analysis and Render ecosystem fetch in parallel
        results = await asyncio.gather(
            *language_tasks,
            fetch_render_ecosystem(github_api, db_pool),
            return_exceptions=True
        )
        
        # Aggregate and store final results
        final_result = await aggregate_results(results, db_pool, execution_start)
        
        return final_result
    finally:
        await cleanup_connections(github_api, db_pool)
```

- Define 3 target languages: Python, TypeScript (Next.js >= 16), Go
- Initialize shared GitHub API client and database connection pool
- Spawn 4 parallel tasks: 3 language tasks + 1 Render ecosystem task
- Use `asyncio.gather()` with `return_exceptions=True` for fault tolerance
- Aggregate results and store execution metrics
- Cleanup connections in finally block

**Task 2: `fetch_language_repos(language: str, github_api, db_pool)`**

```python
@task
async def fetch_language_repos(language: str, github_api, db_pool) -> List[Dict]:
    """Fetch and store trending repos for a specific language."""
    # Search GitHub API
    repos = await github_api.search_repositories(
        language=language,
        sort='stars',
        updated_since=datetime.utcnow() - timedelta(days=30)
    )
    
    # TypeScript-specific filtering for Next.js >= 16
    if language == 'TypeScript':
        repos = await filter_nextjs_repos(repos, github_api, min_version=16)
    
    # Store raw API responses
    await store_raw_repos(repos, db_pool, source_language=language)
    
    # Spawn batch analysis tasks
    batch_results = await analyze_repo_batch(repos[:100], github_api, db_pool)
    
    return batch_results
```

- Search GitHub API: `/search/repositories?q=language:{language}&sort=stars`
- For TypeScript: additional filter for Next.js >= 16 via package.json check
- Filter for repos updated in last 30 days
- Store raw API responses in `raw_github_repos` table using shared db_pool
- Return batch of top 100 repos per language
- Retry config: 3 retries, 60s backoff

**Task 3: `analyze_repo_batch(repos: List[Dict], github_api, db_pool)`**

```python
@task
async def analyze_repo_batch(repos: List[Dict], github_api, db_pool) -> List[Dict]:
    """Analyze a batch of repositories with detailed metrics."""
    enriched_repos = []
    
    # Process repos in batches of 10
    for batch in chunk_list(repos, size=10):
        batch_tasks = [
            analyze_single_repo(repo, github_api, db_pool)
            for repo in batch
        ]
        
        # Gather with exceptions to continue on failures
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Filter out exceptions and collect successful results
        enriched_repos.extend([r for r in batch_results if not isinstance(r, Exception)])
    
    return enriched_repos
```

- Process 10 repos at a time using chunked batches
- Fetch detailed metrics: commits, issues, contributors via shared github_api
- Store raw metrics in `raw_repo_metrics` table
- Check for render.yaml and README badges
- Transform and load into `stg_repos_validated` with data quality scores
- Skip failed repos, continue with batch
- Retry config: 2 retries, 45s backoff

**Task 4: `fetch_render_ecosystem(github_api, db_pool)`**

```python
@task
async def fetch_render_ecosystem(github_api, db_pool) -> List[Dict]:
    """Fetch Render-related projects from multiple sources."""
    # Parallel fetch from multiple sources
    results = await asyncio.gather(
        github_api.get_org_repos('render-examples'),
        github_api.get_org_repos('render'),
        github_api.search_by_topic('render'),
        github_api.search_by_topic('render-deploy'),
        github_api.search_by_topic('render-blueprints'),
        github_api.search_readme_mentions('render.com')
    )
    
    # Deduplicate and store
    unique_repos = deduplicate_repos(results)
    await store_raw_repos(unique_repos, db_pool, source_type='render_ecosystem')
    
    # Analyze Render-specific features
    analyzed = await analyze_render_projects(unique_repos, github_api, db_pool)
    
    return analyzed
```

- Fetch from `render-examples` and `render` orgs in parallel
- Search topics: `render`, `render-deploy`, `render-blueprints`
- Search README mentions of "render.com"
- Check curated list of Render employee GitHub profiles
- Store in `raw_github_repos` with source_type='render_ecosystem'
- Retry config: 3 retries, 60s backoff

**Task 5: `analyze_render_projects(render_repos: List[Dict], github_api, db_pool)`**

```python
@task
async def analyze_render_projects(render_repos: List[Dict], github_api, db_pool) -> List[Dict]:
    """Analyze Render-specific features and categorization."""
    enriched_projects = []
    
    for repo in render_repos:
        # Detect Render usage patterns
        render_data = await detect_render_usage(repo, github_api, db_pool)
        
        # Calculate Render-specific scores
        repo['render_category'] = categorize_render_project(repo)
        repo['blueprint_quality'] = score_blueprint_quality(render_data)
        repo['documentation_score'] = score_documentation(repo, render_data)
        
        enriched_projects.append(repo)
    
    # Store enrichment data
    await store_render_enrichment(enriched_projects, db_pool)
    
    return enriched_projects
```

- Standard metrics + Render-specific scoring
- Blueprint quality: parse render.yaml for service diversity
- Documentation score: deploy button, README quality
- Categorize: official, employee, community, blueprint
- Load enrichment data into `stg_render_enrichment` table
- Retry config: 2 retries, 30s backoff

**Task 6: `detect_render_usage(repo_data: Dict, github_api, db_pool)`**

```python
@task
async def detect_render_usage(repo_data: Dict, github_api, db_pool) -> Dict:
    """Detect Render usage patterns in a repository."""
    owner, name = repo_data['full_name'].split('/')
    
    # Check for render.yaml
    render_yaml = await github_api.get_file_contents(owner, name, 'render.yaml')
    
    # Parse configuration
    render_config = {}
    if render_yaml:
        render_config = parse_render_yaml(render_yaml)
    
    # Check Dockerfile for Render patterns
    dockerfile = await github_api.get_file_contents(owner, name, 'Dockerfile')
    docker_patterns = scan_dockerfile_for_render(dockerfile) if dockerfile else {}
    
    # Calculate complexity score
    complexity = calculate_render_complexity(render_config, docker_patterns)
    
    return {
        'uses_render': bool(render_yaml),
        'render_yaml_content': render_yaml,
        'services': render_config.get('services', []),
        'complexity_score': complexity,
        **docker_patterns
    }
```

- Parse render.yaml to extract services, databases, build commands
- Scan Dockerfile for Render patterns
- Check for Render environment variables
- Calculate complexity score (0-10)
- Retry config: 1 retry

**Task 7: `calculate_metrics(enriched_repos: List[Dict], db_pool)`**

```python
@task
async def calculate_metrics(enriched_repos: List[Dict], db_pool) -> List[Dict]:
    """Calculate momentum and activity scores for repositories."""
    for repo in enriched_repos:
        # Star velocity calculation
        repo['star_velocity'] = (
            (repo.get('stars_last_7_days', 0) / max(repo['stars'], 1)) * 100
        )
        
        # Activity score (weighted formula)
        repo['activity_score'] = (
            repo.get('commits_last_7_days', 0) * 0.4 +
            repo.get('issues_closed_last_7_days', 0) * 0.3 +
            repo.get('active_contributors', 0) * 0.3
        )
        
        # Momentum score
        repo['momentum_score'] = (
            repo['star_velocity'] * 0.4 +
            repo['activity_score'] * 0.6
        )
        
        # Apply Render boost multiplier
        if repo.get('uses_render'):
            repo['momentum_score'] *= 1.2
        
        # Freshness penalty
        age_days = (datetime.utcnow() - repo['created_at']).days
        if age_days > 180:
            repo['momentum_score'] *= 0.9
    
    return enriched_repos
```

- Star velocity: `(stars_last_7_days / total_stars) * 100`
- Activity score: weighted formula using commits, issues, contributors
- Momentum score: `(star_velocity * 0.4) + (activity_score * 0.6)`
- Apply Render boost multiplier (1.2x) for marketing visibility
- Freshness penalty for repos older than 180 days
- Retry config: 1 retry

**Task 8: `aggregate_results(all_results: List, db_pool, execution_start)`**

```python
@task
async def aggregate_results(all_results: List, db_pool, execution_start) -> Dict:
    """Execute ETL pipeline: Extract from staging → Transform → Load to analytics."""
    # Filter successful results (handle exceptions from gather)
    language_results = [r for r in all_results[:3] if not isinstance(r, Exception)]
    render_results = all_results[3] if len(all_results) > 3 and not isinstance(all_results[3], Exception) else []
    
    # Combine and deduplicate
    all_repos = deduplicate_repos(language_results + [render_results])
    
    # Calculate metrics for all repos
    scored_repos = await calculate_metrics(all_repos, db_pool)
    
    # ETL Pipeline Execution
    # 1. Extract: Read from staging tables
    staging_data = await extract_from_staging(db_pool)
    
    # 2. Transform: Calculate rankings and velocity metrics
    ranked_repos = transform_and_rank(
        scored_repos,
        overall_limit=100,
        per_language_limit=50
    )
    
    # 3. Load: Upsert to analytics layer
    await load_to_analytics(ranked_repos, db_pool)
    
    # Store execution stats
    execution_time = (datetime.utcnow() - execution_start).total_seconds()
    await store_execution_stats(execution_time, len(all_repos), db_pool)
    
    return {
        'repos_processed': len(all_repos),
        'execution_time': execution_time,
        'languages': TARGET_LANGUAGES,
        'success': True
    }

async def load_to_analytics(repos: List[Dict], db_pool):
    """Load transformed data into analytics layer."""
    async with db_pool.acquire() as conn:
        # Upsert into dim_repositories (SCD Type 2)
        await upsert_dim_repositories(repos, conn)
        
        # Insert daily snapshots into fact_repo_snapshots
        await insert_fact_snapshots(repos, conn)
        
        # Insert Render usage into fact_render_usage
        render_repos = [r for r in repos if r.get('uses_render')]
        await insert_render_usage(render_repos, conn)
        
        # Link to dim_languages and dim_render_services
        await link_dimensions(repos, conn)
```

- **ETL Pipeline Execution:**
  1. **Extract**: Read from `stg_repos_validated` and `stg_render_enrichment`
  2. **Transform**: Calculate momentum scores, rankings, velocity metrics
  3. **Load**: 
     - Upsert into `dim_repositories` (SCD Type 2)
     - Insert daily snapshots into `fact_repo_snapshots`
     - Insert Render usage into `fact_render_usage`
     - Link to `dim_languages` and `dim_render_services`
- Deduplicate across language and Render datasets
- Calculate rank_overall (top 100) and rank_in_language (top 50 per language)
- Store execution stats in `fact_workflow_executions`
- Retry config: 3 retries, 30s backoff

**Task 9: `store_execution_stats(duration: float, repos_count: int, db_pool)`**

```python
@task
async def store_execution_stats(duration: float, repos_count: int, db_pool) -> None:
    """Record workflow performance metrics."""
    # Calculate parallel speedup (3 languages in parallel vs sequential)
    estimated_sequential = duration * 3
    parallel_speedup = estimated_sequential / duration
    
    stats = {
        'execution_date': datetime.utcnow(),
        'total_duration_seconds': duration,
        'repos_processed': repos_count,
        'tasks_executed': 9,  # Total workflow tasks
        'parallel_speedup_factor': parallel_speedup,
        'languages_processed': TARGET_LANGUAGES,
        'success_rate': 1.0  # Will be calculated from actual task results
    }
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO fact_workflow_executions 
            (execution_date, total_duration_seconds, repos_processed, 
             tasks_executed, parallel_speedup_factor, languages_processed)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, stats['execution_date'], stats['total_duration_seconds'],
             stats['repos_processed'], stats['tasks_executed'],
             stats['parallel_speedup_factor'], stats['languages_processed'])
```

- Record workflow performance data
- Calculate parallel speedup vs sequential (3 languages in parallel)
- Track retry success rates by task type
- Store in `fact_workflow_executions` table with full execution context
- Include languages_processed array and error_details JSON

**Helper Functions:**

```python
async def init_connections():
    """Initialize shared GitHub API client and database pool."""
    github_api = GitHubAPIClient(token=os.getenv('GITHUB_TOKEN'))
    db_pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
    return github_api, db_pool

async def cleanup_connections(github_api, db_pool):
    """Clean up shared resources."""
    await github_api.close()
    await db_pool.close()
```

### Phase 4: Cron Trigger Service

Create `trigger.py` for Render Cron Job:

```python
import asyncio
import aiohttp
import os
from datetime import datetime

async def trigger_workflow():
    """Trigger the main analysis workflow via Render Workflows API."""
    workflow_id = os.getenv('RENDER_WORKFLOW_ID')
    api_key = os.getenv('RENDER_API_KEY')
    
    url = f"https://api.render.com/v1/workflows/{workflow_id}/trigger"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✓ Workflow triggered successfully at {datetime.utcnow()}")
                    print(f"  Execution ID: {result.get('execution_id')}")
                    return result
                else:
                    error_text = await response.text()
                    print(f"✗ Workflow trigger failed: {response.status}")
                    print(f"  Error: {error_text}")
                    return None
    except Exception as e:
        print(f"✗ Exception during workflow trigger: {str(e)}")
        return None

if __name__ == "__main__":
    asyncio.run(trigger_workflow())
```

- Runs hourly: `0 * * * *`
- Triggers workflow via Render Workflows API asynchronously
- Logs execution status and execution ID
- Handles trigger failures gracefully with error logging
- Uses aiohttp for async HTTP requests

Environment variables:

- `RENDER_WORKFLOW_ID` - The workflow to trigger (main_analysis_task)
- `RENDER_API_KEY` - Render API authentication token

### Phase 5: Next.js Dashboard Frontend

Create Next.js 14 app with 6 main pages:

**Page 1: Home `/`**

- Hero with latest workflow stats (repos analyzed, last run time, speedup)
- Query: `fact_workflow_executions` (latest execution)
- Render Spotlight banner (rotating 3 featured projects)
- Filters: language (Python/TypeScript/Go), time range (24h/7d/30d), "Show only Render projects"
- Top 100 repos as cards with metrics
- Query: `analytics_trending_repos_current` view
- Render badge for projects using Render
- "Last updated" indicator with next run countdown

**Page 2: Render Showcase `/render`**

- Hero: "Built with Render"
- Query: `analytics_render_showcase` view
- 4 featured categories (filtered by render_category):
  - Official Blueprints (top 10, category='official')
  - Community Stars (top 15, category='community')
  - Employee Innovation (top 10, category='employee')
  - Workflow Showcase (this project as meta-example)
- Ecosystem stats dashboard: aggregations from `fact_render_usage` (total projects, stars, service adoption)

**Page 3: Language Deep Dive `/language/[lang]`**

- Language header with stats from `dim_languages`
- Query: `analytics_language_rankings` view (filtered by language_name)
- Render projects in this language (separate section, uses_render = TRUE)
- Time-series charts: join `fact_repo_snapshots` for historical trends (star growth, activity scores)
- Sortable table of top 50 repos per language
- Pie chart: Render service adoption aggregated from `fact_render_usage` by language

**Page 4: Repository Detail `/repo/[owner]/[name]`**

- Overview card with all metrics from `dim_repositories` JOIN `fact_repo_snapshots` (current)
- If uses Render: special section from `stg_render_enrichment` showing services, render.yaml link, deploy button, auto-generated architecture diagram
- Historical momentum chart: query `fact_repo_snapshots` WHERE repo_key = X ORDER BY snapshot_date DESC LIMIT 30
- "Why it's trending" insights box (calculated from momentum components)
- Comparison vs similar projects (same language from `analytics_language_rankings`)

**Page 5: Workflow Performance Dashboard `/meta`**

- Latest execution visualization (task tree, status indicators)
- Query: `fact_workflow_executions` ORDER BY execution_date DESC LIMIT 1
- Performance metrics box (duration, speedup, success rate, task count)
- Historical charts: query `fact_workflow_executions` for trends
  - Execution time over last 30 runs
  - Success rate trends
  - Tasks executed/succeeded/failed distribution
- Task breakdown table with retry stats from execution JSON
- Code snippet showcase with annotations (static content)

**Page 6: Marketing Assets `/for-marketing`**

- Featured project cards (exportable as images)
- Auto-generated success stories
- Verified workflow performance claims
- Customer highlights for outreach
- Blueprint spotlight with usage stats
- Export options: CSV, images, embeddable widgets

### Phase 6: Render Configuration

Create `render.yaml` defining all services:

```yaml
services:
  - type: web
    name: trender-dashboard
    runtime: node
    buildCommand: npm install && npm run build
    startCommand: npm start
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: trender-db
          property: connectionString
      - key: NEXT_PUBLIC_API_URL
        value: https://trender-dashboard.onrender.com

  - type: cron
    name: trender-analyzer-cron
    runtime: python
    schedule: "0 * * * *"
    buildCommand: pip install -r requirements.txt
    startCommand: python trigger.py
    envVars:
      - key: RENDER_WORKFLOW_ID
        sync: false
      - key: RENDER_API_KEY
        sync: false

databases:
  - name: trender-db
    databaseName: trender
    plan: standard
```

Separate workflow deployment via Render Workflows CLI/API.

### Phase 7: Marketing Integration Features

Add optional tasks for marketing automation using Render Workflows:

**`generate_marketing_assets(db_pool)`**

```python
@task
async def generate_marketing_assets(db_pool) -> Dict:
    """Generate marketing assets from trending Render projects."""
    async with db_pool.acquire() as conn:
        # Query top 5 Render community projects from analytics view
        top_projects = await conn.fetch("""
            SELECT * FROM analytics_render_showcase
            WHERE render_category = 'community'
            ORDER BY momentum_score DESC
            LIMIT 5
        """)
        
        # Generate social media cards
        assets = []
        for project in top_projects:
            card = await create_social_card(project)
            assets.append({
                'project': project['repo_full_name'],
                'card_url': card,
                'generated_at': datetime.utcnow()
            })
        
        # Store for dashboard access
        await store_marketing_assets(assets, conn)
        
        return {'assets_generated': len(assets)}
```

- Identify top 5 Render community projects weekly
- Generate social media card images
- Store for marketing dashboard access

**`create_monthly_blog_draft(db_pool)`**

```python
@task
async def create_monthly_blog_draft(db_pool) -> Dict:
    """Compile monthly statistics and generate blog draft."""
    async with db_pool.acquire() as conn:
        # Gather monthly statistics
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(DISTINCT repo_key) as total_repos,
                SUM(stars) as total_stars,
                COUNT(DISTINCT CASE WHEN uses_render THEN repo_key END) as render_projects
            FROM analytics_trending_repos_current
            WHERE snapshot_date >= NOW() - INTERVAL '30 days'
        """)
        
        # Get top projects
        top_projects = await conn.fetch("""
            SELECT repo_full_name, stars, momentum_score, language
            FROM analytics_trending_repos_current
            ORDER BY momentum_score DESC
            LIMIT 10
        """)
        
        # Generate markdown blog draft
        blog_content = format_blog_post(stats, top_projects)
        
        return {
            'blog_draft': blog_content,
            'word_count': len(blog_content.split())
        }
```

- Compile monthly statistics from `fact_repo_snapshots`
- Format top projects and ecosystem growth
- Generate markdown blog post draft

**`identify_success_stories(db_pool)`**

```python
@task
async def identify_success_stories(db_pool) -> List[Dict]:
    """Find projects meeting case study criteria."""
    async with db_pool.acquire() as conn:
        candidates = await conn.fetch("""
            SELECT 
                dr.repo_full_name,
                dr.repo_url,
                fs.stars,
                fs.momentum_score,
                sr.render_services,
                sr.service_count
            FROM dim_repositories dr
            JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
            LEFT JOIN stg_render_enrichment sr ON dr.repo_full_name = sr.repo_full_name
            WHERE dr.uses_render = TRUE
              AND fs.stars >= 500
              AND fs.star_velocity >= 50  -- 50%+ growth
              AND fs.snapshot_date = CURRENT_DATE
            ORDER BY fs.momentum_score DESC
        """)
        
        # Enrich with contact info (GitHub API)
        enriched_candidates = []
        for candidate in candidates:
            contact_info = await fetch_repo_contact_info(candidate)
            enriched_candidates.append({**candidate, **contact_info})
        
        # Store leads
        await store_success_story_leads(enriched_candidates, conn)
        
        return enriched_candidates
```

- Find projects meeting case study criteria (500+ stars, 50% growth, uses Render)
- Enrich with contact info via GitHub API
- Store leads for outreach in database

**`analyze_deployment_platforms(github_api, db_pool)`**

```python
@task
async def analyze_deployment_platforms(github_api, db_pool) -> Dict:
    """Compare Render adoption vs competitors."""
    platforms = ['render', 'vercel', 'railway', 'fly.io']
    
    platform_stats = {}
    for platform in platforms:
        # Search for platform usage patterns
        repos = await github_api.search_readme_mentions(platform)
        
        platform_stats[platform] = {
            'total_repos': len(repos),
            'total_stars': sum(r.get('stars', 0) for r in repos),
            'avg_stars': sum(r.get('stars', 0) for r in repos) / len(repos) if repos else 0
        }
    
    # Generate competitive report
    report = generate_competitive_report(platform_stats)
    
    # Store in database
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO platform_intelligence 
            (report_date, platform_data, summary)
            VALUES ($1, $2, $3)
        """, datetime.utcnow(), platform_stats, report)
    
    return platform_stats
```

- Compare Render adoption vs competitors (Vercel, Railway, Fly)
- Generate competitive intelligence report
- Store in database for trend analysis

**`track_blueprint_metrics(github_api, db_pool)`**

```python
@task
async def track_blueprint_metrics(github_api, db_pool) -> Dict:
    """Monitor blueprint usage and performance."""
    async with db_pool.acquire() as conn:
        blueprints = await conn.fetch("""
            SELECT * FROM analytics_render_showcase
            WHERE render_category = 'blueprint'
            AND has_blueprint_button = TRUE
        """)
        
        metrics = []
        for blueprint in blueprints:
            # Fetch deployment metrics (would use Render API)
            deploy_stats = await fetch_blueprint_deploy_stats(blueprint)
            
            # Calculate performance score
            performance = {
                'blueprint': blueprint['repo_full_name'],
                'total_deploys': deploy_stats.get('deploys', 0),
                'avg_deploy_time': deploy_stats.get('avg_time', 0),
                'success_rate': deploy_stats.get('success_rate', 0),
                'underperforming': deploy_stats.get('success_rate', 1) < 0.8
            }
            
            metrics.append(performance)
        
        # Store metrics
        await store_blueprint_metrics(metrics, conn)
        
        return {
            'blueprints_tracked': len(metrics),
            'underperforming': sum(1 for m in metrics if m['underperforming'])
        }
```

- Monitor blueprint usage, deploys, time-to-deploy
- Flag underperforming blueprints (success rate < 80%)
- Store metrics in `fact_render_usage` table

### Phase 8: Testing and Optimization

**Workflow Testing:**
- Test `@task` decorator integration with Render Workflows SDK
- Verify shared resource initialization (github_api, db_pool) in `init_connections()`
- Test async/await pattern with `asyncio.gather()` for parallel execution
- Verify parallel task execution (3 languages simultaneously: Python, TypeScript, Go)
- Test fault tolerance with `return_exceptions=True` (continue if one language fails)
- Verify proper resource cleanup in finally blocks
- Test workflow trigger via Render API from cron job

**API and Data Testing:**
- Test GitHub API rate limit handling with async client
- Test async batch processing with aiohttp
- Validate TypeScript Next.js >= 16 filtering logic
- Validate Render detection logic (render.yaml parsing)
- Test retry mechanisms with simulated failures in @task functions
- Test ETL pipeline data flow: Raw → Staging → Analytics
- Verify data quality scoring in staging layer
- Validate SCD Type 2 logic for dim_repositories

**Performance Optimization:**
- Optimize database connection pool size (min_size=5, max_size=20)
- Test concurrent database writes with asyncpg
- Optimize database queries for dashboard performance (analytics views)
- Verify parallel speedup calculation (3x expected)
- Test sub-second task spin-up times
- Monitor memory usage with shared resources

**Frontend Testing:**
- Test all frontend pages with mock and live data
- Verify calculation formulas (momentum score, Render boost)
- Test real-time workflow status updates on meta page
- Verify analytics views render correctly

## Key Implementation Notes

**Language-Specific Filtering:**

- **Python**: Standard language filter, focus on general-purpose and data engineering projects
- **TypeScript**: Additional filter for Next.js >= 16 via package.json validation
  - Fetch package.json from repo
  - Check `dependencies.next` or `devDependencies.next` version
  - Only include repos with Next >= 16.0.0
- **Go**: Standard language filter, focus on systems and CLI tools

**Batch Processing Emphasis:**

- Hourly execution via cron, not continuous
- Results update periodically, shown as "Last updated X minutes ago"
- Next run countdown indicator on dashboard
- Historical snapshots for trend analysis via `fact_repo_snapshots`

**Render Workflows Showcase:**

- **SDK Pattern**: All tasks use `@task` decorator from `render_sdk.workflows`
- **Shared Resources**: GitHub API client and DB pool initialized once, passed to all tasks
- **Async Execution**: Full async/await pattern with `asyncio.gather()` for parallelism
- **Track and display execution metrics** (speedup, task count, retry success)
- **Visualize parallel task execution** (3 languages + 1 Render ecosystem task = 4 parallel streams)
- **Demonstrate fault tolerance** (continue if one language fails via `return_exceptions=True`)
- **Show sub-second task spin-up times** from workflow execution logs
- **Resource management**: Proper cleanup in finally blocks
- **Store detailed execution data** in `fact_workflow_executions` for meta-analysis

**Render Ecosystem Focus:**

- Separate showcase page for Render projects
- Boost multiplier for Render projects in ranking
- Special badges and "Deploy to Render" buttons
- Architecture visualizations from render.yaml

**Scalability Considerations:**

- Start with 3 languages (Python, TypeScript, Go), easily expandable to 50+
- Batch size of 10 repos per `analyze_repo_batch` task
- Rate limit buffer of 100 requests before throttling
- Layered data architecture allows historical analysis and reprocessing
- Database indexes on language, momentum_score, uses_render, snapshot_date
- SCD Type 2 in dim_repositories enables tracking repository changes over time

## Success Metrics

**Technical:**

- Process 300+ repos across 3 languages in under 10 seconds
- 3x speedup vs sequential processing (parallel language fetching)
- 99%+ success rate on workflow runs
- Sub-second task spin-up times
- Data quality score >= 0.90 for 95%+ of repositories in staging layer
- Complete ETL pipeline execution (Raw → Staging → Analytics) in single workflow run

**Marketing:**

- Showcase 50+ Render ecosystem projects
- Auto-generate weekly social media content
- Identify 5+ case study candidates per month
- Track competitive platform adoption trends

## Repository Structure

```
trender/
├── workflows/
│   ├── workflow.py           # Main workflow tasks with @task decorators
│   ├── github_api.py         # GitHub API client with async methods
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── extract.py        # Raw layer extraction
│   │   ├── transform.py      # Staging layer transformations
│   │   ├── load.py           # Analytics layer loading (fact/dim)
│   │   └── data_quality.py   # Data quality scoring
│   ├── metrics.py            # Calculation logic (momentum, velocity)
│   ├── render_detection.py  # Render usage detection
│   ├── connections.py        # Shared resource initialization
│   └── requirements.txt      # render-sdk, asyncpg, aiohttp
├── trigger/
│   ├── trigger.py            # Async cron trigger script
│   └── requirements.txt      # aiohttp
├── dashboard/
│   ├── app/
│   │   ├── page.tsx          # Home - trending overview
│   │   ├── render/page.tsx   # Render showcase
│   │   ├── language/[lang]/page.tsx  # Language deep dive
│   │   ├── repo/[owner]/[name]/page.tsx  # Repo detail
│   │   ├── meta/page.tsx     # Workflow performance
│   │   └── for-marketing/page.tsx    # Marketing assets
│   ├── components/
│   ├── lib/
│   │   ├── db.ts             # PostgreSQL connection
│   │   └── queries.ts        # Analytics view queries
│   ├── package.json
│   └── tailwind.config.js
├── database/
│   ├── schema/
│   │   ├── 01_raw_layer.sql       # Raw tables
│   │   ├── 02_staging_layer.sql   # Staging tables
│   │   ├── 03_analytics_layer.sql # Fact/dim tables
│   │   └── 04_views.sql           # Analytics views
│   └── init.sql              # Master initialization script
├── .env.example              # Environment variables template
├── render.yaml               # Render configuration
└── README.md
```

**Key Files:**

**`workflows/workflow.py`** - Main orchestration with Render Workflows SDK:
```python
from render_sdk.workflows import task
import asyncio
from typing import Dict, List
from datetime import datetime, timedelta

# All task functions decorated with @task
# Shared resources (github_api, db_pool) passed as parameters
# Async/await pattern throughout
```

**`workflows/connections.py`** - Shared resource management:
```python
import asyncpg
import os
from github_api import GitHubAPIClient

async def init_connections():
    """Initialize shared GitHub API client and database pool."""
    github_api = GitHubAPIClient(token=os.getenv('GITHUB_TOKEN'))
    db_pool = await asyncpg.create_pool(
        os.getenv('DATABASE_URL'),
        min_size=5,
        max_size=20
    )
    return github_api, db_pool

async def cleanup_connections(github_api, db_pool):
    """Clean up shared resources."""
    await github_api.close()
    await db_pool.close()
```

**`workflows/requirements.txt`**:
```
render-sdk>=1.0.0
asyncpg>=0.29.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
```

## Deployment Steps

1. **Create Render PostgreSQL database**
   - Provision a PostgreSQL instance on Render
   - Note the connection string for `DATABASE_URL`

2. **Initialize database schema in layers:**
   - Run `01_raw_layer.sql` (raw tables)
   - Run `02_staging_layer.sql` (staging tables)
   - Run `03_analytics_layer.sql` (fact/dimension tables)
   - Run `04_views.sql` (analytics views)

3. **Deploy Render Workflows with workflow.py**
   - Install Render Workflows SDK: `pip install render-sdk`
   - Deploy workflow: `render-workflows deploy workflow.py`
   - Set entry point as `main_analysis_task`
   - Configure environment variables (GITHUB_TOKEN, DATABASE_URL)
   - Note the WORKFLOW_ID for trigger service

4. **Create Render Cron Job with trigger.py**
   - Deploy as Render Cron Job
   - Set schedule: `0 * * * *` (hourly)
   - Configure environment variables (RENDER_WORKFLOW_ID, RENDER_API_KEY)
   - Initial state: disabled until first manual run completes

5. **Deploy Next.js dashboard as Render Web Service**
   - Deploy from `/dashboard` directory
   - Configure DATABASE_URL environment variable
   - Set build command: `npm install && npm run build`
   - Set start command: `npm start`

6. **Configure environment variables** (use .env.example as template)
   - GitHub API token with repo read permissions
   - Database connection string
   - Render Workflow ID and API key
   - Next.js public URLs

7. **Trigger first manual workflow run** to populate all data layers
   - Use Render Workflows CLI: `render-workflows trigger {WORKFLOW_ID}`
   - Or trigger via API endpoint from trigger.py
   - Monitor execution: verify all @task functions complete successfully

8. **Verify data pipeline: Raw → Staging → Analytics**
   - Check `raw_github_repos` has entries
   - Check `stg_repos_validated` has validated data
   - Check `dim_repositories` and `fact_repo_snapshots` populated
   - Verify data quality scores in staging layer

9. **Verify dashboard displays results from analytics views**
   - Access dashboard URL
   - Check home page shows trending repos
   - Verify language pages render correctly
   - Check workflow performance page shows execution stats

10. **Enable hourly cron schedule**
    - Enable cron job in Render dashboard
    - Monitor first scheduled execution
    - Verify continuous data updates

