-- Migration 002: Remove uses_render flag, use language='render' instead
-- This migration updates the schema to identify Render repos by language='render' 
-- instead of maintaining a separate uses_render boolean flag

-- Step 1: Add 'render' language to dim_languages if not exists
INSERT INTO dim_languages (language_name, language_category, ecosystem_size)
VALUES ('render', 'platform', 'medium')
ON CONFLICT (language_name) DO NOTHING;

-- Step 2: Remove uses_render column from stg_repos_validated
ALTER TABLE stg_repos_validated DROP COLUMN IF EXISTS uses_render;

-- Step 3: Drop old index on uses_render (staging)
DROP INDEX IF EXISTS idx_stg_repos_render;

-- Step 4: Create new index on language for render repos (staging)
CREATE INDEX IF NOT EXISTS idx_stg_repos_render ON stg_repos_validated(language) WHERE language = 'render';

-- Step 5: Drop views that depend on uses_render column
DROP VIEW IF EXISTS analytics_trending_repos_current;
DROP VIEW IF EXISTS analytics_render_showcase;
DROP VIEW IF EXISTS analytics_language_rankings;
DROP VIEW IF EXISTS analytics_language_trends;

-- Step 6: Remove uses_render column from dim_repositories
ALTER TABLE dim_repositories DROP COLUMN IF EXISTS uses_render;

-- Step 7: Drop old index on uses_render (analytics)
DROP INDEX IF EXISTS idx_dim_repos_render;

-- Step 8: Create new index on language for render repos (analytics)
CREATE INDEX IF NOT EXISTS idx_dim_repos_render ON dim_repositories(language) WHERE language = 'render';

-- Step 9: Recreate views to use language='render' instead of uses_render flag
-- analytics_trending_repos_current
CREATE OR REPLACE VIEW analytics_trending_repos_current AS
SELECT
  dr.repo_full_name,
  dr.repo_url,
  dr.language,
  dr.description,
  dr.readme_content,
  (dr.language = 'render') as uses_render,
  dr.render_category,
  fs.stars,
  fs.star_velocity,
  fs.activity_score,
  fs.momentum_score,
  fs.rank_overall,
  fs.rank_in_language,
  fs.snapshot_date,
  fs.snapshot_date as last_updated
FROM dim_repositories dr
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE dr.is_current = TRUE
  AND fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
ORDER BY fs.momentum_score DESC;

-- analytics_render_showcase
CREATE OR REPLACE VIEW analytics_render_showcase AS
SELECT
  dr.repo_full_name,
  dr.repo_url,
  dr.language,
  dr.description,
  dr.readme_content,
  dr.render_category,
  fs.stars,
  fs.momentum_score,
  fs.star_velocity,
  fs.activity_score,
  sre.render_services,
  sre.service_count,
  sre.render_complexity_score,
  sre.has_blueprint_button,
  sre.deploy_button_url,
  fs.snapshot_date
FROM dim_repositories dr
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
LEFT JOIN stg_render_enrichment sre ON dr.repo_full_name = sre.repo_full_name
WHERE dr.is_current = TRUE
  AND dr.language = 'render'
  AND fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
ORDER BY fs.momentum_score DESC;

-- analytics_language_rankings
CREATE OR REPLACE VIEW analytics_language_rankings AS
SELECT
  dl.language_name,
  dr.repo_full_name,
  dr.repo_url,
  dr.description,
  dr.readme_content,
  (dr.language = 'render') as uses_render,
  dr.render_category,
  fs.stars,
  fs.momentum_score,
  fs.star_velocity,
  fs.rank_in_language,
  fs.snapshot_date,
  COUNT(CASE WHEN dr.language = 'render' THEN 1 END) OVER (PARTITION BY dl.language_name) as render_adoption_count
FROM dim_languages dl
JOIN dim_repositories dr ON dl.language_name = dr.language
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE dr.is_current = TRUE
  AND fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
  AND fs.rank_in_language <= 50
ORDER BY dl.language_name, fs.rank_in_language;

-- analytics_language_trends
CREATE OR REPLACE VIEW analytics_language_trends AS
SELECT
  dl.language_name,
  dl.language_category,
  COUNT(DISTINCT dr.repo_key) as total_repos,
  SUM(fs.stars) as total_stars,
  AVG(fs.stars) as avg_stars,
  AVG(fs.momentum_score) as avg_momentum,
  COUNT(CASE WHEN dr.language = 'render' THEN 1 END) as render_projects,
  ROUND((COUNT(CASE WHEN dr.language = 'render' THEN 1 END)::DECIMAL / NULLIF(COUNT(DISTINCT dr.repo_key), 0)) * 100, 2) as render_adoption_percentage
FROM dim_languages dl
LEFT JOIN dim_repositories dr ON dl.language_name = dr.language AND dr.is_current = TRUE
LEFT JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
   OR fs.snapshot_date IS NULL
GROUP BY dl.language_key, dl.language_name, dl.language_category
ORDER BY total_repos DESC;

-- Note: analytics_render_services_adoption and analytics_repo_history views don't reference uses_render, so no changes needed

