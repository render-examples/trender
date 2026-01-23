-- Check if data is being loaded from staging to analytics

\echo '=== STAGING DATA READY TO LOAD ==='
SELECT 
    language,
    COUNT(*) as repos_in_staging,
    COUNT(CASE WHEN data_quality_score >= 0.70 THEN 1 END) as high_quality_repos
FROM stg_repos_validated
GROUP BY language
ORDER BY language;

\echo '\n=== ANALYTICS DATA LOADED ==='
SELECT 
    language,
    COUNT(*) as repos_in_analytics
FROM dim_repositories
WHERE is_current = TRUE
GROUP BY language
ORDER BY language;

\echo '\n=== SAMPLE REPOS IN DIM_REPOSITORIES ==='
SELECT 
    repo_full_name,
    language,
    uses_render,
    created_at
FROM dim_repositories
WHERE is_current = TRUE
ORDER BY repo_key DESC
LIMIT 10;

\echo '\n=== CHECK IF AGGREGATE RAN ==='
SELECT 
    execution_date,
    repos_processed,
    total_duration_seconds,
    tasks_succeeded,
    tasks_failed
FROM fact_workflow_executions
ORDER BY execution_date DESC
LIMIT 3;

