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

TRUNCATE TABLE fact_render_usage CASCADE;
TRUNCATE TABLE fact_repo_snapshots CASCADE;

-- =======================
-- ANALYTICS LAYER (Dimension Tables)
-- =======================
-- Clear dimension tables (will cascade to any remaining facts)

TRUNCATE TABLE dim_render_services RESTART IDENTITY CASCADE;
TRUNCATE TABLE dim_languages RESTART IDENTITY CASCADE;
TRUNCATE TABLE dim_repositories RESTART IDENTITY CASCADE;

-- =======================
-- STAGING LAYER
-- =======================
-- Clear staging tables

TRUNCATE TABLE stg_render_enrichment CASCADE;
TRUNCATE TABLE stg_repos_validated RESTART IDENTITY CASCADE;

-- =======================
-- RAW LAYER
-- =======================
-- Clear raw ingestion tables

TRUNCATE TABLE raw_repo_metrics RESTART IDENTITY CASCADE;
TRUNCATE TABLE raw_github_repos RESTART IDENTITY CASCADE;

-- =======================
-- RE-SEED DIMENSION TABLES
-- =======================
-- Re-insert seed data for dimension tables that need it

-- Re-seed dim_languages with the 3 target languages
INSERT INTO dim_languages (language_name, language_category, ecosystem_size) VALUES
  ('Python', 'general', 'large'),
  ('TypeScript', 'web', 'large'),
  ('Go', 'systems', 'large');

-- Re-seed dim_render_services with Render service types
INSERT INTO dim_render_services (service_type, service_description) VALUES
  ('web', 'Web Service - HTTP servers, APIs, websites'),
  ('worker', 'Background Worker - Async task processing'),
  ('cron', 'Cron Job - Scheduled tasks'),
  ('private', 'Private Service - Internal services'),
  ('static', 'Static Site - Pre-built sites'),
  ('postgres', 'PostgreSQL Database'),
  ('redis', 'Redis Database');

COMMIT;

-- =======================
-- VERIFICATION
-- =======================
-- Check that all tables are empty (except seeded dimension tables)

SELECT 'raw_github_repos' as table_name, COUNT(*) as row_count FROM raw_github_repos
UNION ALL
SELECT 'raw_repo_metrics', COUNT(*) FROM raw_repo_metrics
UNION ALL
SELECT 'stg_repos_validated', COUNT(*) FROM stg_repos_validated
UNION ALL
SELECT 'stg_render_enrichment', COUNT(*) FROM stg_render_enrichment
UNION ALL
SELECT 'dim_repositories', COUNT(*) FROM dim_repositories
UNION ALL
SELECT 'dim_languages', COUNT(*) FROM dim_languages
UNION ALL
SELECT 'dim_render_services', COUNT(*) FROM dim_render_services
UNION ALL
SELECT 'fact_repo_snapshots', COUNT(*) FROM fact_repo_snapshots
UNION ALL
SELECT 'fact_render_usage', COUNT(*) FROM fact_render_usage
ORDER BY table_name;

