-- Workflow execution traces
-- Tracks detailed timing and status information for workflow runs
-- Supports observability and debugging of the ETL pipeline

-- Main workflow runs table
CREATE TABLE IF NOT EXISTS fact_workflow_runs (
  run_id VARCHAR(255) PRIMARY KEY,
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  status VARCHAR(50) NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
  task_tree JSONB NOT NULL,
  error_message TEXT,
  repos_processed INTEGER,
  execution_time_seconds NUMERIC(10, 2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_workflow_runs_completed 
  ON fact_workflow_runs(completed_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_status 
  ON fact_workflow_runs(status);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_started 
  ON fact_workflow_runs(started_at DESC);

-- GIN index for JSONB queries on task_tree
CREATE INDEX IF NOT EXISTS idx_workflow_runs_task_tree 
  ON fact_workflow_runs USING GIN (task_tree);

-- Comments for documentation
COMMENT ON TABLE fact_workflow_runs IS 
  'Stores execution traces for workflow runs with hierarchical task timing data';

COMMENT ON COLUMN fact_workflow_runs.run_id IS 
  'Unique identifier for the workflow run (from Render Workflows SDK)';

COMMENT ON COLUMN fact_workflow_runs.task_tree IS 
  'Hierarchical JSON structure containing task names, start/end times, and status';

COMMENT ON COLUMN fact_workflow_runs.execution_time_seconds IS 
  'Total execution time in seconds (completed_at - started_at)';

