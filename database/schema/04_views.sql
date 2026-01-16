-- Analytics Views
-- Optimized views for dashboard queries

-- View: analytics_trending_repos_current
-- Purpose: Current top trending repositories across all languages
CREATE OR REPLACE VIEW analytics_trending_repos_current AS
SELECT
  dr.repo_full_name,
  dr.repo_url,
  dr.language,
  dr.description,
  dr.uses_render,
  dr.render_category,
  fs.stars,
  fs.forks,
  fs.star_velocity,
  fs.activity_score,
  fs.momentum_score,
  fs.rank_overall,
  fs.rank_in_language,
  fs.commits_last_7_days,
  fs.issues_closed_last_7_days,
  fs.active_contributors,
  fs.snapshot_date,
  fs.snapshot_date as last_updated
FROM dim_repositories dr
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE dr.is_current = TRUE
  AND fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
ORDER BY fs.momentum_score DESC;

-- View: analytics_render_showcase
-- Purpose: Render ecosystem showcase with enrichment data
CREATE OR REPLACE VIEW analytics_render_showcase AS
SELECT
  dr.repo_full_name,
  dr.repo_url,
  dr.language,
  dr.description,
  dr.render_category,
  fs.stars,
  fs.forks,
  fs.momentum_score,
  fs.star_velocity,
  fs.activity_score,
  fs.commits_last_7_days,
  fs.active_contributors,
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
  AND dr.uses_render = TRUE
  AND fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
ORDER BY fs.momentum_score DESC;

-- View: analytics_language_rankings
-- Purpose: Per-language top performers with Render adoption stats
CREATE OR REPLACE VIEW analytics_language_rankings AS
SELECT
  dl.language_name,
  dr.repo_full_name,
  dr.repo_url,
  dr.description,
  dr.uses_render,
  dr.render_category,
  fs.stars,
  fs.forks,
  fs.momentum_score,
  fs.star_velocity,
  fs.rank_in_language,
  fs.commits_last_7_days,
  fs.active_contributors,
  fs.snapshot_date,
  COUNT(CASE WHEN dr.uses_render THEN 1 END) OVER (PARTITION BY dl.language_name) as render_adoption_count
FROM dim_languages dl
JOIN dim_repositories dr ON dl.language_name = dr.language
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE dr.is_current = TRUE
  AND fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
  AND fs.rank_in_language <= 50
ORDER BY dl.language_name, fs.rank_in_language;

-- View: analytics_workflow_performance
-- Purpose: Latest workflow execution performance metrics
CREATE OR REPLACE VIEW analytics_workflow_performance AS
SELECT
  execution_date,
  total_duration_seconds,
  repos_processed,
  tasks_executed,
  tasks_succeeded,
  tasks_failed,
  tasks_retried,
  parallel_speedup_factor,
  languages_processed,
  success_rate,
  ROUND((tasks_succeeded::DECIMAL / NULLIF(tasks_executed, 0)) * 100, 2) as task_success_percentage
FROM fact_workflow_executions
ORDER BY execution_date DESC;

-- View: analytics_render_services_adoption
-- Purpose: Render service type adoption statistics
CREATE OR REPLACE VIEW analytics_render_services_adoption AS
SELECT
  drs.service_type,
  drs.service_description,
  COUNT(DISTINCT fru.repo_key) as repos_using_service,
  SUM(fru.service_count) as total_service_instances,
  AVG(fru.complexity_score) as avg_complexity_score,
  COUNT(CASE WHEN fru.has_blueprint THEN 1 END) as blueprints_with_service
FROM dim_render_services drs
LEFT JOIN fact_render_usage fru ON drs.service_key = fru.service_key
WHERE fru.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_render_usage)
   OR fru.snapshot_date IS NULL
GROUP BY drs.service_key, drs.service_type, drs.service_description
ORDER BY repos_using_service DESC;

-- View: analytics_language_trends
-- Purpose: Language-level aggregated statistics
CREATE OR REPLACE VIEW analytics_language_trends AS
SELECT
  dl.language_name,
  dl.language_category,
  COUNT(DISTINCT dr.repo_key) as total_repos,
  SUM(fs.stars) as total_stars,
  AVG(fs.stars) as avg_stars,
  AVG(fs.momentum_score) as avg_momentum,
  COUNT(CASE WHEN dr.uses_render THEN 1 END) as render_projects,
  ROUND((COUNT(CASE WHEN dr.uses_render THEN 1 END)::DECIMAL / NULLIF(COUNT(DISTINCT dr.repo_key), 0)) * 100, 2) as render_adoption_percentage
FROM dim_languages dl
LEFT JOIN dim_repositories dr ON dl.language_name = dr.language AND dr.is_current = TRUE
LEFT JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE fs.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_repo_snapshots)
   OR fs.snapshot_date IS NULL
GROUP BY dl.language_key, dl.language_name, dl.language_category
ORDER BY total_repos DESC;

-- View: analytics_repo_history
-- Purpose: Historical trends for individual repositories (for charting)
CREATE OR REPLACE VIEW analytics_repo_history AS
SELECT
  dr.repo_full_name,
  dr.language,
  fs.snapshot_date,
  fs.stars,
  fs.forks,
  fs.star_velocity,
  fs.momentum_score,
  fs.activity_score,
  fs.commits_last_7_days,
  fs.active_contributors,
  fs.rank_overall,
  fs.rank_in_language
FROM dim_repositories dr
JOIN fact_repo_snapshots fs ON dr.repo_key = fs.repo_key
WHERE dr.is_current = TRUE
ORDER BY dr.repo_full_name, fs.snapshot_date DESC;
