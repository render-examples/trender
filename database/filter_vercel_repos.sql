-- Update views to filter out vercel repositories (including vercel/, vercel-labs/, etc.)
-- Run this script to apply the filter: psql $DATABASE_URL -f database/filter_vercel_repos.sql

-- Drop and recreate views to avoid column conflicts
DROP VIEW IF EXISTS analytics_trending_repos_current CASCADE;
DROP VIEW IF EXISTS analytics_render_showcase CASCADE;
DROP VIEW IF EXISTS analytics_language_rankings CASCADE;
DROP VIEW IF EXISTS analytics_language_trends CASCADE;
DROP VIEW IF EXISTS analytics_repo_history CASCADE;

-- View: analytics_trending_repos_current
CREATE VIEW analytics_trending_repos_current AS
SELECT
  dr.repo_full_name,
  dr.repo_url,
  dr.language,
  dr.description,
  dr.readme_content,
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
  AND dr.repo_full_name !~ '^vercel'
ORDER BY fs.momentum_score DESC;

-- View: analytics_render_showcase
CREATE VIEW analytics_render_showcase AS
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
  AND dr.repo_full_name !~ '^vercel'
ORDER BY fs.momentum_score DESC;

-- View: analytics_language_rankings
CREATE VIEW analytics_language_rankings AS
SELECT
  dl.language_name,
  dr.repo_full_name,
  dr.repo_url,
  dr.description,
  dr.readme_content,
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
  AND dr.repo_full_name !~ '^vercel'
ORDER BY dl.language_name, fs.rank_in_language;

-- View: analytics_language_trends
CREATE VIEW analytics_language_trends AS
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
LEFT JOIN dim_repositories dr ON dl.language_name = dr.language AND dr.is_current = TRUE AND dr.repo_full_name !~ '^vercel'
LEFT JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
   OR fs.snapshot_date IS NULL
GROUP BY dl.language_key, dl.language_name, dl.language_category
ORDER BY total_repos DESC;

-- View: analytics_repo_history
CREATE VIEW analytics_repo_history AS
SELECT
  dr.repo_full_name,
  dr.language,
  fs.snapshot_date,
  fs.stars,
  fs.star_velocity,
  fs.momentum_score,
  fs.activity_score,
  fs.rank_overall,
  fs.rank_in_language
FROM dim_repositories dr
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE dr.is_current = TRUE
  AND dr.repo_full_name !~ '^vercel'
ORDER BY dr.repo_full_name, fs.snapshot_date DESC;

-- Verification query
SELECT 'Views updated successfully! Vercel repos will be filtered out.' AS status;
SELECT COUNT(*) as total_repos_visible FROM analytics_trending_repos_current;
SELECT COUNT(*) as vercel_repos_excluded FROM dim_repositories WHERE is_current = TRUE AND repo_full_name ~ '^vercel';
