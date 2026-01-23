-- Migration: Remove fact_workflow_executions table
-- This table is no longer needed as we don't track workflow execution metrics
-- Run this script to clean up existing databases

\echo 'Removing fact_workflow_executions table and related view...'

-- Drop the view that depends on the table
DROP VIEW IF EXISTS analytics_workflow_performance CASCADE;

-- Drop the table
DROP TABLE IF EXISTS fact_workflow_executions CASCADE;

\echo '✓ fact_workflow_executions table removed'
\echo '✓ analytics_workflow_performance view removed'
\echo ''
\echo 'Migration complete!'
\echo 'Database now has:'
\echo '  - 9 tables (down from 10)'
\echo '  - 6 views (down from 7)'

