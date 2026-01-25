-- Staging Layer - Validated and Enriched Data
-- Cleaned data with business rules applied

-- Table: stg_repos_validated
-- Purpose: Cleaned and validated repository data with quality scores
CREATE TABLE IF NOT EXISTS stg_repos_validated (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) UNIQUE NOT NULL,
  repo_url TEXT NOT NULL,
  language VARCHAR(50) NOT NULL,
  description TEXT,
  stars INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  uses_render BOOLEAN DEFAULT FALSE,
  readme_content TEXT,
  loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT valid_stars CHECK (stars >= 0)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_stg_repos_language ON stg_repos_validated(language);
CREATE INDEX IF NOT EXISTS idx_stg_repos_updated ON stg_repos_validated(updated_at);
CREATE INDEX IF NOT EXISTS idx_stg_repos_stars ON stg_repos_validated(stars DESC);
CREATE INDEX IF NOT EXISTS idx_stg_repos_render ON stg_repos_validated(uses_render) WHERE uses_render = TRUE;

-- Table: stg_render_enrichment
-- Purpose: Render-specific enrichment data
CREATE TABLE IF NOT EXISTS stg_render_enrichment (
  id SERIAL PRIMARY KEY,
  repo_full_name VARCHAR(255) UNIQUE NOT NULL REFERENCES stg_repos_validated(repo_full_name) ON DELETE CASCADE,
  render_category VARCHAR(50), -- 'official', 'employee', 'community', 'blueprint'
  render_services TEXT[],
  has_blueprint_button BOOLEAN DEFAULT FALSE,
  render_complexity_score INTEGER CHECK (render_complexity_score BETWEEN 0 AND 10),
  deploy_button_url TEXT,
  service_count INTEGER,
  loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT valid_render_category CHECK (render_category IN ('official', 'employee', 'community', 'blueprint'))
);

-- Indexes for Render enrichment queries
CREATE INDEX IF NOT EXISTS idx_stg_render_category ON stg_render_enrichment(render_category);
CREATE INDEX IF NOT EXISTS idx_stg_render_services ON stg_render_enrichment USING GIN(render_services);
