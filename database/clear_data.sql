-- Clear Data Script
-- Purpose: Remove all data from tables without dropping the tables
-- This script maintains the schema structure but removes all rows
-- Note: Views are not affected as they contain no data themselves

-- =======================
-- IMPORTANT NOTES
-- =======================
-- 1. This script uses TRUNCATE for better performance and automatic CASCADE
-- 2. Foreign key relationships are respected via CASCADE
-- 3. Sequences (auto-increment IDs) are RESET to start from 1 again
-- 4. Dimension seed data (languages, services) will also be removed and must be re-seeded
-- 5. Views remain intact (they don't store data)

BEGIN;

-- =======================
-- ANALYTICS LAYER (Fact Tables First)
-- =======================
-- Clear fact tables that reference dimension tables

TRUNCATE TABLE fact_repo_snapshots CASCADE;

-- =======================
-- ANALYTICS LAYER (Dimension Tables)
-- =======================
-- Clear dimension tables (will cascade to any remaining facts)

TRUNCATE TABLE dim_languages RESTART IDENTITY CASCADE;
TRUNCATE TABLE dim_repositories RESTART IDENTITY CASCADE;

-- =======================
-- STAGING LAYER
-- =======================
-- Clear staging tables

TRUNCATE TABLE stg_repos_validated RESTART IDENTITY CASCADE;

-- =======================
-- RAW LAYER
-- =======================
-- Clear raw ingestion tables

TRUNCATE TABLE raw_github_repos RESTART IDENTITY CASCADE;

-- =======================
-- RE-SEED DIMENSION TABLES
-- =======================
-- Re-insert seed data for dimension tables that need it

-- Re-seed dim_languages with all 4 tracked languages
INSERT INTO dim_languages (language_name, language_category, ecosystem_size) VALUES
  ('Python', 'general', 'large'),
  ('TypeScript', 'web', 'large'),
  ('Go', 'systems', 'large'),
  ('render', 'platform', 'medium');

COMMIT;

-- =======================
-- VERIFICATION
-- =======================
-- Check that all tables are empty (except seeded dimension tables)

SELECT 'raw_github_repos' as table_name, COUNT(*) as row_count FROM raw_github_repos
UNION ALL
SELECT 'stg_repos_validated', COUNT(*) FROM stg_repos_validated
UNION ALL
SELECT 'dim_repositories', COUNT(*) FROM dim_repositories
UNION ALL
SELECT 'dim_languages', COUNT(*) FROM dim_languages
UNION ALL
SELECT 'fact_repo_snapshots', COUNT(*) FROM fact_repo_snapshots
ORDER BY table_name;

