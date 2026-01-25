-- Fix repos that were found via render code search but got unmarked
-- This script marks repos as uses_render=true if they appear in stg_render_enrichment
-- (which means they were found via code search but the flag got cleared)

BEGIN;

-- Update stg_repos_validated to mark repos that have render enrichment data
UPDATE stg_repos_validated srv
SET uses_render = TRUE
FROM stg_render_enrichment sre
WHERE srv.repo_full_name = sre.repo_full_name
  AND srv.uses_render = FALSE;

-- Check results
SELECT 
    COUNT(*) FILTER (WHERE uses_render = TRUE) as render_repos,
    COUNT(*) as total_repos
FROM stg_repos_validated;

-- Also update the analytics layer
UPDATE dim_repositories dr
SET uses_render = TRUE
FROM stg_render_enrichment sre
WHERE dr.repo_full_name = sre.repo_full_name
  AND dr.uses_render = FALSE
  AND dr.is_current = TRUE;

-- Verify analytics layer
SELECT 
    COUNT(*) FILTER (WHERE uses_render = TRUE) as render_repos,
    COUNT(*) as total_repos
FROM dim_repositories
WHERE is_current = TRUE;

COMMIT;

