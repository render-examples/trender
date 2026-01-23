-- Query to get row counts for all tables
-- Usage: psql $DATABASE_URL -f database/row_counts.sql

-- Format output nicely
\pset border 2
\pset format wrapped

-- Add title
\echo '\n========================================='
\echo '         TABLE ROW COUNTS'
\echo '=========================================\n'

SELECT 
    table_name,
    TO_CHAR(row_count, '999,999,999') as row_count
FROM (
    SELECT 'dim_languages' as table_name, COUNT(*) as row_count FROM dim_languages
    UNION ALL
    SELECT 'dim_render_services', COUNT(*) FROM dim_render_services
    UNION ALL
    SELECT 'dim_repositories', COUNT(*) FROM dim_repositories
    UNION ALL
    SELECT 'fact_render_usage', COUNT(*) FROM fact_render_usage
    UNION ALL
    SELECT 'fact_repo_snapshots', COUNT(*) FROM fact_repo_snapshots
    UNION ALL
    -- fact_workflow_executions removed - not needed
    UNION ALL
    SELECT 'raw_github_repos', COUNT(*) FROM raw_github_repos
    UNION ALL
    SELECT 'raw_repo_metrics', COUNT(*) FROM raw_repo_metrics
    UNION ALL
    SELECT 'stg_render_enrichment', COUNT(*) FROM stg_render_enrichment
    UNION ALL
    SELECT 'stg_repos_validated', COUNT(*) FROM stg_repos_validated
) counts
ORDER BY table_name;

-- Add footer with total
\echo '\n-----------------------------------------'
SELECT 
    'TOTAL' as summary,
    TO_CHAR(SUM(row_count), '999,999,999') as total_rows
FROM (
    SELECT COUNT(*) as row_count FROM dim_languages
    UNION ALL
    SELECT COUNT(*) FROM dim_render_services
    UNION ALL
    SELECT COUNT(*) FROM dim_repositories
    UNION ALL
    SELECT COUNT(*) FROM fact_render_usage
    UNION ALL
    SELECT COUNT(*) FROM fact_repo_snapshots
    UNION ALL
    0 -- fact_workflow_executions removed
    UNION ALL
    SELECT COUNT(*) FROM raw_github_repos
    UNION ALL
    SELECT COUNT(*) FROM raw_repo_metrics
    UNION ALL
    SELECT COUNT(*) FROM stg_render_enrichment
    UNION ALL
    SELECT COUNT(*) FROM stg_repos_validated
) all_counts;

