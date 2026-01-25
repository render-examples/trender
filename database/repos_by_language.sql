-- Check Repos by Language in stg_repos_validated
-- Run this to diagnose TypeScript and Go data quality issues

\echo '\n=== 1. REPO COUNTS BY LANGUAGE ==='
SELECT 
    language,
    COUNT(*) as total_repos,
    COUNT(CASE WHEN language = 'render' THEN 1 END) as render_repos,
    AVG(stars) as avg_stars
FROM stg_repos_validated
GROUP BY language
ORDER BY total_repos DESC;

\echo '\n=== 2. RECENT REPOS BY LANGUAGE (Last 24 Hours) ==='
SELECT 
    language,
    COUNT(*) as repos_loaded_24h,
    MAX(loaded_at) as last_loaded,
    MIN(loaded_at) as first_loaded
FROM stg_repos_validated
WHERE loaded_at >= NOW() - INTERVAL '24 hours'
GROUP BY language
ORDER BY repos_loaded_24h DESC;

\echo '\n=== 3. SAMPLE TYPESCRIPT REPOS (Top 5 by Stars) ==='
SELECT 
    repo_full_name,
    stars,
    forks,
    open_issues,
    commits_last_7_days,
    issues_closed_last_7_days,
    active_contributors,
    created_at,
    loaded_at,
    CASE 
        WHEN description IS NULL OR description = '' THEN '❌ MISSING'
        WHEN description = 'N/A' OR description = 'placeholder' THEN '⚠️  PLACEHOLDER'
        ELSE '✓ OK'
    END as description_status,
    CASE 
        WHEN commits_last_7_days = 0 AND issues_closed_last_7_days = 0 AND active_contributors = 0 
        THEN '⚠️  ALL METRICS ZERO'
        ELSE '✓ HAS DATA'
    END as metrics_status
FROM stg_repos_validated
WHERE language = 'TypeScript'
ORDER BY stars DESC
LIMIT 5;

\echo '\n=== 4. SAMPLE GO REPOS (Top 5 by Stars) ==='
SELECT 
    repo_full_name,
    stars,
    forks,
    open_issues,
    commits_last_7_days,
    issues_closed_last_7_days,
    active_contributors,
    created_at,
    loaded_at,
    CASE 
        WHEN description IS NULL OR description = '' THEN '❌ MISSING'
        WHEN description = 'N/A' OR description = 'placeholder' THEN '⚠️  PLACEHOLDER'
        ELSE '✓ OK'
    END as description_status,
    CASE 
        WHEN commits_last_7_days = 0 AND issues_closed_last_7_days = 0 AND active_contributors = 0 
        THEN '⚠️  ALL METRICS ZERO'
        ELSE '✓ HAS DATA'
    END as metrics_status
FROM stg_repos_validated
WHERE language = 'Go'
ORDER BY stars DESC
LIMIT 5;

\echo '\n=== 5. SAMPLE PYTHON REPOS (Top 5 by Stars for Comparison) ==='
SELECT 
    repo_full_name,
    stars,
    forks,
    open_issues,
    commits_last_7_days,
    issues_closed_last_7_days,
    active_contributors,
    created_at,
    loaded_at,
    CASE 
        WHEN description IS NULL OR description = '' THEN '❌ MISSING'
        WHEN description = 'N/A' OR description = 'placeholder' THEN '⚠️  PLACEHOLDER'
        ELSE '✓ OK'
    END as description_status
FROM stg_repos_validated
WHERE language = 'Python'
ORDER BY stars DESC
LIMIT 5;

\echo '\n=== 6. REPOS WITH MISSING DESCRIPTIONS ==='
SELECT 
    language,
    repo_full_name,
    stars,
    commits_last_7_days,
    issues_closed_last_7_days,
    active_contributors,
    CASE 
        WHEN description IS NULL OR description = '' THEN 'No description'
        WHEN LENGTH(description) < 20 THEN 'Short description'
        ELSE 'Has description'
    END as desc_status
FROM stg_repos_validated
WHERE description IS NULL OR description = '' OR LENGTH(description) < 20
ORDER BY language, stars DESC
LIMIT 10;

\echo '\n=== 7. REPOS WITH PLACEHOLDER/MISSING DESCRIPTIONS ==='
SELECT 
    language,
    COUNT(*) as count_with_issues,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM stg_repos_validated WHERE language = srv.language) as pct
FROM stg_repos_validated srv
WHERE description IS NULL 
   OR description = '' 
   OR description = 'N/A' 
   OR description = 'placeholder'
GROUP BY language
ORDER BY count_with_issues DESC;

\echo '\n=== 8. REPOS WITH ALL ZERO METRICS (Potential API Failures) ==='
SELECT 
    language,
    COUNT(*) as repos_with_zero_metrics
FROM stg_repos_validated
WHERE commits_last_7_days = 0 
  AND issues_closed_last_7_days = 0 
  AND active_contributors = 0
GROUP BY language
ORDER BY repos_with_zero_metrics DESC;

\echo '\n=== 9. MOST RECENT LOADS BY LANGUAGE ==='
SELECT 
    language,
    repo_full_name,
    stars,
    loaded_at,
    AGE(NOW(), loaded_at) as time_since_load
FROM stg_repos_validated
WHERE language IN ('Python', 'TypeScript', 'Go')
ORDER BY loaded_at DESC
LIMIT 15;

\echo '\n=== 10. AGGREGATE STATS COMPARISON ==='
SELECT 
    language,
    COUNT(*) as total,
    AVG(stars) as avg_stars,
    AVG(commits_last_7_days) as avg_commits_7d,
    AVG(issues_closed_last_7_days) as avg_issues_closed_7d,
    AVG(active_contributors) as avg_contributors,
    COUNT(CASE WHEN commits_last_7_days > 0 THEN 1 END) as repos_with_commit_data
FROM stg_repos_validated
WHERE language IN ('Python', 'TypeScript', 'Go')
GROUP BY language
ORDER BY total DESC;

