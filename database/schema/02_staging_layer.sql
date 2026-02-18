-- Staging Layer - Validated and Enriched Data
-- Cleaned data with business rules applied

-- Table: stg_repos_validated
-- Purpose: Cleaned and validated repository data with quality scores
-- Note: Render repos are identified by language='render' (no separate uses_render flag needed)
CREATE TABLE IF NOT EXISTS stg_repos_validated (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) UNIQUE NOT NULL,
  repo_url TEXT NOT NULL,
  language VARCHAR(50) NOT NULL,
  description TEXT,
  stars INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  readme_content TEXT,
  loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT valid_stars CHECK (stars >= 0)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_stg_repos_language ON stg_repos_validated(language);
CREATE INDEX IF NOT EXISTS idx_stg_repos_updated ON stg_repos_validated(updated_at);
CREATE INDEX IF NOT EXISTS idx_stg_repos_stars ON stg_repos_validated(stars DESC);
CREATE INDEX IF NOT EXISTS idx_stg_repos_render ON stg_repos_validated(language) WHERE language = 'render';
