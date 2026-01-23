-- Raw Layer - Ingestion Tables
-- Stores unprocessed data from GitHub API

-- Table: raw_github_repos
-- Purpose: Store complete GitHub API responses for repositories
CREATE TABLE IF NOT EXISTS raw_github_repos (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) NOT NULL,
  api_response JSONB NOT NULL,
  readme_content TEXT,
  fetch_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  source_language VARCHAR(50),
  source_type VARCHAR(20), -- 'trending', 'render_ecosystem'
  CONSTRAINT valid_source_type CHECK (source_type IN ('trending', 'render_ecosystem'))
);

-- Unique constraint to prevent duplicates - one row per repo (latest data)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'raw_github_repos_repo_unique'
  ) THEN
    ALTER TABLE raw_github_repos ADD CONSTRAINT raw_github_repos_repo_unique UNIQUE (repo_full_name);
  END IF;
END $$;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_raw_repos_fetch ON raw_github_repos(fetch_timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_repos_source ON raw_github_repos(source_type, source_language);

-- Table: raw_repo_metrics
-- Purpose: Store detailed GitHub metrics (commits, issues, contributors)
CREATE TABLE IF NOT EXISTS raw_repo_metrics (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) NOT NULL,
  metric_type VARCHAR(50) NOT NULL, -- 'commits', 'issues', 'contributors'
  metric_data JSONB NOT NULL,
  fetch_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT valid_metric_type CHECK (metric_type IN ('commits', 'issues', 'contributors'))
);

-- Unique constraint to prevent duplicates - one row per repo per metric type (latest data)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'raw_repo_metrics_unique'
  ) THEN
    ALTER TABLE raw_repo_metrics ADD CONSTRAINT raw_repo_metrics_unique UNIQUE (repo_full_name, metric_type);
  END IF;
END $$;

-- Indexes for querying metrics
CREATE INDEX IF NOT EXISTS idx_raw_metrics_repo ON raw_repo_metrics(repo_full_name);
CREATE INDEX IF NOT EXISTS idx_raw_metrics_type ON raw_repo_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_raw_metrics_fetch ON raw_repo_metrics(fetch_timestamp);
