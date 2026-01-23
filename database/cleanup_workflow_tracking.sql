-- Simple cleanup query to remove workflow execution tracking
-- This removes the view and table that are no longer used

-- Step 1: Drop the view that queries the table
DROP VIEW IF EXISTS analytics_workflow_performance CASCADE;

-- Step 2: Drop the fact table
DROP TABLE IF EXISTS fact_workflow_executions CASCADE;

-- Verify removal (optional - run after the above)
-- SELECT COUNT(*) FROM information_schema.tables 
-- WHERE table_name IN ('fact_workflow_executions', 'analytics_workflow_performance');

