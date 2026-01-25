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

\echo ''
\echo '=========================================='
\echo 'Database initialization complete!'
\echo '=========================================='
\echo ''
\echo 'RAW LAYER (2 tables):'
\echo '  - raw_github_repos: Complete GitHub API responses (JSONB)'
\echo '  - raw_repo_metrics: Detailed metrics counts (commits, issues, contributors)'
\echo ''
\echo 'STAGING LAYER (2 tables):'
\echo '  - stg_repos_validated: Cleaned and validated repositories'
\echo '  - stg_render_enrichment: Render service configs and complexity'
\echo ''
\echo 'ANALYTICS LAYER - DIMENSIONS (3 tables):'
\echo '  - dim_repositories: Repo master data (SCD Type 2)'
\echo '  - dim_languages: Language metadata (Python, TypeScript, Go)'
\echo '  - dim_render_services: Service types (web, worker, cron, etc.)'
\echo ''
\echo 'ANALYTICS LAYER - FACTS (2 tables):'
\echo '  - fact_repo_snapshots: Daily metrics and momentum scores'
\echo '  - fact_render_usage: Service adoption by repository'
\echo ''
\echo 'ANALYTICS VIEWS (6 views):'
\echo '  - analytics_trending_repos_current: Top trending repos'
\echo '  - analytics_render_showcase: Render ecosystem showcase'
\echo '  - analytics_language_rankings: Per-language rankings'
\echo '  - analytics_render_services_adoption: Service usage stats'
\echo '  - analytics_language_trends: Language-level aggregates'
\echo '  - analytics_repo_history: Historical repo trends'
\echo ''
\echo 'Total: 9 tables + 6 views'
\echo ''
