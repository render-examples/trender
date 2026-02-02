-- Data Retention Cleanup Script
-- Purpose: Implement tiered retention policy to control storage growth
-- - Raw layer: 7 days (debugging and reprocessing)
-- - Staging layer: 7 days (ETL audit trail)
-- - Analytics layer: 30 days (trending analysis and dashboard history)
--
-- This script is designed to run after each successful workflow execution
-- to maintain predictable storage costs and prevent unbounded growth.

BEGIN;

-- ====================================
-- RETENTION POLICY CONFIGURATION
-- ====================================
-- Raw/Staging: 7 days
-- Analytics: 30 days

-- ====================================
-- RAW LAYER CLEANUP (7-day retention)
-- ====================================
-- Delete raw GitHub API responses older than 7 days
-- Uses indexed fetch_timestamp for efficient deletion

DELETE FROM raw_github_repos
WHERE fetch_timestamp < NOW() - INTERVAL '7 days';

-- Delete raw metrics data older than 7 days
-- Uses indexed fetch_timestamp for efficient deletion

DELETE FROM raw_repo_metrics
WHERE fetch_timestamp < NOW() - INTERVAL '7 days';

-- ====================================
-- STAGING LAYER CLEANUP (7-day retention)
-- ====================================
-- Delete staging enrichment data older than 7 days
-- Cascades to stg_render_enrichment due to foreign key

DELETE FROM stg_render_enrichment
WHERE loaded_at < NOW() - INTERVAL '7 days';

-- Delete staging validated repos older than 7 days
-- This maintains a 7-day buffer for debugging ETL issues

DELETE FROM stg_repos_validated
WHERE loaded_at < NOW() - INTERVAL '7 days';

-- ====================================
-- ANALYTICS LAYER CLEANUP (30-day retention)
-- ====================================
-- Delete render usage facts older than 30 days
-- Uses indexed snapshot_date for efficient deletion

DELETE FROM fact_render_usage
WHERE snapshot_date < CURRENT_DATE - INTERVAL '30 days';

-- Delete repo snapshot facts older than 30 days
-- Uses indexed snapshot_date for efficient deletion

DELETE FROM fact_repo_snapshots
WHERE snapshot_date < CURRENT_DATE - INTERVAL '30 days';

-- ====================================
-- DIMENSION HISTORY CLEANUP (30-day retention)
-- ====================================
-- Delete old dimension versions (SCD Type 2 history)
-- Only removes expired versions (is_current = FALSE)
-- Keeps current versions regardless of age

DELETE FROM dim_repositories
WHERE is_current = FALSE
  AND valid_to IS NOT NULL
  AND valid_to < NOW() - INTERVAL '30 days';

-- ====================================
-- SUMMARY REPORT
-- ====================================
-- Return counts of remaining rows per table
-- This helps monitor data growth and retention effectiveness

SELECT 
    'RETENTION SUMMARY' as report_type,
    NOW() as cleanup_timestamp;

SELECT 
    'raw_github_repos' as table_name,
    COUNT(*) as row_count,
    MIN(fetch_timestamp) as oldest_record,
    MAX(fetch_timestamp) as newest_record
FROM raw_github_repos
UNION ALL
SELECT 
    'raw_repo_metrics',
    COUNT(*),
    MIN(fetch_timestamp),
    MAX(fetch_timestamp)
FROM raw_repo_metrics
UNION ALL
SELECT 
    'stg_repos_validated',
    COUNT(*),
    MIN(loaded_at),
    MAX(loaded_at)
FROM stg_repos_validated
UNION ALL
SELECT 
    'stg_render_enrichment',
    COUNT(*),
    MIN(loaded_at),
    MAX(loaded_at)
FROM stg_render_enrichment
UNION ALL
SELECT 
    'fact_repo_snapshots',
    COUNT(*),
    MIN(snapshot_date)::timestamptz,
    MAX(snapshot_date)::timestamptz
FROM fact_repo_snapshots
UNION ALL
SELECT 
    'fact_render_usage',
    COUNT(*),
    MIN(snapshot_date)::timestamptz,
    MAX(snapshot_date)::timestamptz
FROM fact_render_usage
UNION ALL
SELECT 
    'dim_repositories (current)',
    COUNT(*),
    MIN(valid_from),
    MAX(valid_from)
FROM dim_repositories
WHERE is_current = TRUE
UNION ALL
SELECT 
    'dim_repositories (history)',
    COUNT(*),
    MIN(valid_from),
    MAX(valid_to)
FROM dim_repositories
WHERE is_current = FALSE
ORDER BY table_name;

COMMIT;

-- ====================================
-- USAGE NOTES
-- ====================================
-- This script is automatically executed by the workflow after successful ETL runs.
-- For manual execution: psql $DATABASE_URL -f database/data_retention_cleanup.sql
-- 
-- Expected steady-state storage (after 30+ days):
-- - ~700 rows in raw layer (7 days × ~100 repos/day)
-- - ~700 rows in staging layer (7 days × ~100 repos/day)
-- - ~3,000 rows in analytics layer (30 days × ~100 repos/day)
--
-- The retention windows are:
-- - Raw/Staging: Keep last 7 days for debugging
-- - Analytics: Keep last 30 days for trending analysis

