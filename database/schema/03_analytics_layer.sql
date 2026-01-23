-- Analytics Layer - Dimensional Model
-- Fact and dimension tables optimized for analytics queries

-- =======================
-- DIMENSION TABLES
-- =======================

-- Dimension: dim_repositories
-- Purpose: Repository dimension with SCD Type 2 (track changes over time)
CREATE TABLE IF NOT EXISTS dim_repositories (
  repo_key SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) NOT NULL,
  repo_url TEXT NOT NULL,
  description TEXT,
  readme_content TEXT,
  language VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  uses_render BOOLEAN DEFAULT FALSE,
  render_category VARCHAR(50),
  valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_to TIMESTAMPTZ,
  is_current BOOLEAN DEFAULT TRUE,
  CONSTRAINT valid_render_category CHECK (render_category IN ('official', 'employee', 'community', 'blueprint', NULL))
);

-- Indexes for dim_repositories
CREATE INDEX IF NOT EXISTS idx_dim_repos_name_current ON dim_repositories(repo_full_name, is_current);
CREATE INDEX IF NOT EXISTS idx_dim_repos_language ON dim_repositories(language);
CREATE INDEX IF NOT EXISTS idx_dim_repos_render ON dim_repositories(uses_render) WHERE uses_render = TRUE;
CREATE INDEX IF NOT EXISTS idx_dim_repos_valid ON dim_repositories(valid_from, valid_to);

-- Dimension: dim_languages
-- Purpose: Language dimension with metadata
CREATE TABLE IF NOT EXISTS dim_languages (
  language_key SERIAL PRIMARY KEY,
  language_name VARCHAR(50) UNIQUE NOT NULL,
  language_category VARCHAR(50), -- 'general', 'web', 'systems', etc.
  ecosystem_size VARCHAR(20) -- 'small', 'medium', 'large'
);

-- Seed data for dim_languages
INSERT INTO dim_languages (language_name, language_category, ecosystem_size) VALUES
  ('Python', 'general', 'large'),
  ('TypeScript', 'web', 'large'),
  ('Go', 'systems', 'large')
ON CONFLICT (language_name) DO NOTHING;

-- Dimension: dim_render_services
-- Purpose: Render service types dimension
CREATE TABLE IF NOT EXISTS dim_render_services (
  service_key SERIAL PRIMARY KEY,
  service_type VARCHAR(50) UNIQUE NOT NULL, -- 'web', 'worker', 'cron', 'private', etc.
  service_description TEXT
);

-- Seed data for dim_render_services
INSERT INTO dim_render_services (service_type, service_description) VALUES
  ('web', 'Web Service - HTTP servers, APIs, websites'),
  ('worker', 'Background Worker - Async task processing'),
  ('cron', 'Cron Job - Scheduled tasks'),
  ('private', 'Private Service - Internal services'),
  ('static', 'Static Site - Pre-built sites'),
  ('postgres', 'PostgreSQL Database'),
  ('redis', 'Redis Database')
ON CONFLICT (service_type) DO NOTHING;

-- =======================
-- FACT TABLES
-- =======================

-- Fact: fact_repo_snapshots
-- Purpose: Time-series metrics (daily snapshots)
CREATE TABLE IF NOT EXISTS fact_repo_snapshots (
  snapshot_id SERIAL PRIMARY KEY,
  repo_key INTEGER NOT NULL REFERENCES dim_repositories(repo_key) ON DELETE CASCADE,
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
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(repo_key, snapshot_date)
);

-- Indexes for fact_repo_snapshots
CREATE INDEX IF NOT EXISTS idx_fact_snapshots_date ON fact_repo_snapshots(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_fact_snapshots_momentum ON fact_repo_snapshots(momentum_score DESC);
CREATE INDEX IF NOT EXISTS idx_fact_snapshots_language ON fact_repo_snapshots(language_key, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_fact_snapshots_repo ON fact_repo_snapshots(repo_key, snapshot_date DESC);

-- Fact: fact_render_usage
-- Purpose: Render service usage facts
CREATE TABLE IF NOT EXISTS fact_render_usage (
  usage_id SERIAL PRIMARY KEY,
  repo_key INTEGER NOT NULL REFERENCES dim_repositories(repo_key) ON DELETE CASCADE,
  service_key INTEGER NOT NULL REFERENCES dim_render_services(service_key),
  snapshot_date DATE NOT NULL,
  service_count INTEGER DEFAULT 1,
  complexity_score INTEGER,
  has_blueprint BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(repo_key, service_key, snapshot_date)
);

-- Indexes for fact_render_usage
CREATE INDEX IF NOT EXISTS idx_fact_render_repo ON fact_render_usage(repo_key, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_fact_render_service ON fact_render_usage(service_key);
CREATE INDEX IF NOT EXISTS idx_fact_render_date ON fact_render_usage(snapshot_date DESC);

-- Fact: fact_workflow_executions
-- Purpose: Workflow performance metrics
CREATE TABLE IF NOT EXISTS fact_workflow_executions (
  execution_id SERIAL PRIMARY KEY,
  execution_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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

-- Indexes for fact_workflow_executions
CREATE INDEX IF NOT EXISTS idx_fact_executions_date ON fact_workflow_executions(execution_date DESC);
CREATE INDEX IF NOT EXISTS idx_fact_executions_success ON fact_workflow_executions(success_rate);
