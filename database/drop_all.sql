-- Drop all tables (in reverse dependency order)
-- Run this to reset the database completely

\echo 'Dropping all tables...'

-- Drop views first
DROP VIEW IF EXISTS vw_top_repos_by_language CASCADE;
DROP VIEW IF EXISTS vw_render_adoption_trends CASCADE;
DROP VIEW IF EXISTS vw_repository_velocity CASCADE;
DROP VIEW IF EXISTS vw_render_service_usage CASCADE;
DROP VIEW IF EXISTS vw_trending_repos_enriched CASCADE;
DROP VIEW IF EXISTS vw_daily_snapshot_summary CASCADE;
DROP VIEW IF EXISTS vw_workflow_performance CASCADE;

-- Drop fact tables
DROP TABLE IF EXISTS fact_workflow_executions CASCADE;
DROP TABLE IF EXISTS fact_render_usage CASCADE;
DROP TABLE IF EXISTS fact_repo_snapshots CASCADE;

-- Drop dimension tables
DROP TABLE IF EXISTS dim_render_services CASCADE;
DROP TABLE IF EXISTS dim_languages CASCADE;
DROP TABLE IF EXISTS dim_repositories CASCADE;

-- Drop staging tables
DROP TABLE IF EXISTS stg_render_enrichment CASCADE;
DROP TABLE IF EXISTS stg_repos_validated CASCADE;

-- Drop raw tables
DROP TABLE IF EXISTS raw_repo_metrics CASCADE;
DROP TABLE IF EXISTS raw_github_repos CASCADE;

\echo 'All tables dropped successfully!'
\echo 'Run init.sql to recreate the database schema.'

