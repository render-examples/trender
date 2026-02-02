import { NextResponse } from 'next/server'
import { query } from '@/lib/db'

export const dynamic = 'force-dynamic'

/**
 * Feature flag: Set to true to return dummy data for development/testing
 * Set to false to query real workflow data from the database
 */
const DUMMY_DATA = false

/**
 * GET /api/workflow-status
 * 
 * Returns the most recent completed workflow run with full task tree and metadata.
 * Used by the WorkflowPanel component to display execution details.
 */
export async function GET() {
  if (DUMMY_DATA) {
    return NextResponse.json(createDummyWorkflowData())
  }

  try {
    const result = await query(
      `SELECT 
        run_id,
        started_at,
        completed_at,
        status,
        task_tree,
        error_message,
        repos_processed,
        execution_time_seconds
      FROM fact_workflow_runs
      WHERE completed_at IS NOT NULL
      ORDER BY completed_at DESC
      LIMIT 1`
    )

    if (result.rows.length === 0) {
      return NextResponse.json(
        { error: 'No workflow runs found yet' },
        { status: 404 }
      )
    }

    const workflowRun = result.rows[0]

    return NextResponse.json({
      run_id: workflowRun.run_id,
      started_at: workflowRun.started_at,
      completed_at: workflowRun.completed_at,
      status: workflowRun.status,
      task_tree: workflowRun.task_tree,
      error_message: workflowRun.error_message,
      repos_processed: workflowRun.repos_processed,
      execution_time_seconds: workflowRun.execution_time_seconds,
    })
  } catch (error) {
    console.error('Error fetching workflow status:', error)
    return NextResponse.json(
      { error: 'Failed to fetch workflow status' },
      { status: 500 }
    )
  }
}

/**
 * Creates dummy workflow data for testing the timeline visualization
 * This simulates a realistic workflow execution with parallel and sequential tasks
 */
function createDummyWorkflowData() {
  const workflowStart = new Date('2026-02-01T10:00:00Z')
  const totalDuration = 120 // 2 minutes total
  
  /**
   * Helper to create timestamp offset from workflow start
   */
  const addSeconds = (seconds: number): string => {
    const date = new Date(workflowStart)
    date.setSeconds(date.getSeconds() + seconds)
    return date.toISOString()
  }

  return {
    run_id: 'dummy-run-123',
    started_at: workflowStart.toISOString(),
    completed_at: addSeconds(totalDuration),
    status: 'completed',
    repos_processed: 150,
    execution_time_seconds: totalDuration,
    error_message: null,
    task_tree: {
      name: 'main_analysis_task',
      started_at: workflowStart.toISOString(),
      completed_at: addSeconds(totalDuration),
      status: 'completed',
      children: [
        {
          name: 'fetch_language_repos',
          language: 'Python',
          started_at: addSeconds(5),
          completed_at: addSeconds(35),
          status: 'completed',
          children: [
            {
              name: 'analyze_repo_batch',
              started_at: addSeconds(10),
              completed_at: addSeconds(25),
              status: 'completed',
            },
          ],
        },
        {
          name: 'fetch_language_repos',
          language: 'TypeScript',
          started_at: addSeconds(30),
          completed_at: addSeconds(65),
          status: 'completed',
          children: [
            {
              name: 'analyze_repo_batch',
              started_at: addSeconds(35),
              completed_at: addSeconds(55),
              status: 'completed',
            },
          ],
        },
        {
          name: 'fetch_language_repos',
          language: 'Go',
          started_at: addSeconds(60),
          completed_at: addSeconds(95),
          status: 'completed',
          children: [
            {
              name: 'analyze_repo_batch',
              started_at: addSeconds(70),
              completed_at: addSeconds(85),
              status: 'completed',
            },
          ],
        },
        {
          name: 'fetch_render_repos',
          started_at: addSeconds(8),
          completed_at: addSeconds(40),
          status: 'completed',
        },
        {
          name: 'aggregate_results',
          started_at: addSeconds(95),
          completed_at: addSeconds(110),
          status: 'completed',
        },
        {
          name: 'cleanup_old_data',
          started_at: addSeconds(110),
          completed_at: addSeconds(120),
          status: 'completed',
        },
      ],
    },
  }
}

