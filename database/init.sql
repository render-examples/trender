-- Trender Database Initialization Script
-- Run this script to create all database tables, indexes, and views
-- Schema follows 3-layer architecture: Raw → Staging → Analytics

-- ====================================
-- LAYER 1: RAW DATA INGESTION
-- ====================================
\echo 'Creating Raw Layer tables...'
\i schema/01_raw_layer.sql

-- ====================================
-- LAYER 2: STAGING (VALIDATED DATA)
-- ====================================
\echo 'Creating Staging Layer tables...'
\i schema/02_staging_layer.sql

-- ====================================
-- LAYER 3: ANALYTICS (DIMENSIONAL MODEL)
-- ====================================
\echo 'Creating Analytics Layer tables...'
\i schema/03_analytics_layer.sql

-- ====================================
-- ANALYTICS VIEWS
-- ====================================
\echo 'Creating Analytics Views...'
\i schema/04_views.sql

\echo 'Database initialization complete!'
\echo 'Tables created: raw_github_repos, raw_repo_metrics, stg_repos_validated, stg_render_enrichment'
\echo 'Dimensions: dim_repositories, dim_languages, dim_render_services'
\echo 'Facts: fact_repo_snapshots, fact_render_usage, fact_workflow_executions'
\echo 'Views: 7 analytics views created'
