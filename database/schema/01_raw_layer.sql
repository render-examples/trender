-- Raw Layer - Ingestion Tables
-- Stores unprocessed data from GitHub API

-- Table: raw_github_repos
-- Purpose: Store complete GitHub API responses for repositories
CREATE TABLE IF NOT EXISTS raw_github_repos (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) NOT NULL,
  api_response JSONB NOT NULL,
  readme_content TEXT,
  fetch_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_language VARCHAR(50)
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
CREATE INDEX IF NOT EXISTS idx_raw_repos_language ON raw_github_repos(source_language);
