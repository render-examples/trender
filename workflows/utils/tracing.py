"""
Workflow tracing utilities for observability and debugging.
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
import asyncpg

logger = logging.getLogger(__name__)


class WorkflowTrace:
    """
    Helper class to track workflow execution with hierarchical task timing.

    Provides structured logging of task execution for observability.
    Stores execution traces in the database for debugging and visualization.
    """

    def __init__(self, run_id: Optional[str] = None):
        """Initialize a new workflow trace with a unique run ID."""
        self.run_id = run_id or f"wfr_{uuid.uuid4().hex[:12]}"
        self.started_at = datetime.now(timezone.utc)
        self.completed_at = None
        self.status = 'running'
        self.task_tree = {
            'name': 'main_analysis_task',
            'started_at': self.started_at.isoformat(),
            'completed_at': None,
            'status': 'running',
            'children': []
        }
        self.repos_processed = 0
        self.error_message = None

    def add_task(self, task_name: str, language: Optional[str] = None) -> Dict:
        """Add a new top-level task to the tree and return its reference."""
        task = {
            'name': task_name,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None,
            'status': 'running',
            'children': []
        }
        if language:
            task['language'] = language
        self.task_tree['children'].append(task)
        return task

    def complete_task(self, task_ref: Dict, status: str = 'completed'):
        """Mark a task as completed with the given status."""
        task_ref['completed_at'] = datetime.now(timezone.utc).isoformat()
        task_ref['status'] = status

    def add_subtask(self, parent_task: Dict, subtask_name: str) -> Dict:
        """Add a subtask under a parent task (for nested task hierarchies)."""
        subtask = {
            'name': subtask_name,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None,
            'status': 'running',
        }
        parent_task['children'].append(subtask)
        return subtask

    def complete(self, status: str = 'completed', error_message: Optional[str] = None):
        """Mark the entire workflow as completed."""
        self.completed_at = datetime.now(timezone.utc)
        self.status = status
        self.error_message = error_message
        self.task_tree['completed_at'] = self.completed_at.isoformat()
        self.task_tree['status'] = status

    async def persist(self, db_pool: asyncpg.Pool):
        """
        Persist the workflow trace to the database.

        Note: Failures during persistence are logged but don't fail the workflow.
        This ensures tracing issues don't impact the main ETL pipeline.
        """
        try:
            execution_time = (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at else None
            )

            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO fact_workflow_runs
                        (run_id, started_at, completed_at, status, task_tree,
                         error_message, repos_processed, execution_time_seconds)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (run_id) DO UPDATE SET
                        completed_at = EXCLUDED.completed_at,
                        status = EXCLUDED.status,
                        task_tree = EXCLUDED.task_tree,
                        error_message = EXCLUDED.error_message,
                        repos_processed = EXCLUDED.repos_processed,
                        execution_time_seconds = EXCLUDED.execution_time_seconds
                """, self.run_id, self.started_at, self.completed_at, self.status,
                    json.dumps(self.task_tree), self.error_message,
                    self.repos_processed, execution_time)

            logger.info(f"Workflow trace persisted: {self.run_id} ({self.status})")
        except Exception as e:
            logger.error(f"Failed to persist workflow trace: {e}")
            # Don't fail the workflow if tracing fails
