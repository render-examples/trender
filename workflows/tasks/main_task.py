"""
Main workflow orchestration task.
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List
from app import app
from connections import cleanup_connections
from utils import WorkflowTrace, init_connections_with_error_handling, process_task_result, add_task_to_trace
from etl import aggregate_results
from tasks.language_tasks import fetch_language_repos, fetch_render_repos

logger = logging.getLogger(__name__)

# Development mode - set to limit processing for faster iteration
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'

# Target languages for analysis
TARGET_LANGUAGES = ['Python', 'TypeScript', 'Go']


async def run_dev_mode_pipeline(trace: WorkflowTrace, execution_start: datetime) -> Dict:
    """
    Run development mode pipeline (Python only + ETL).

    Args:
        trace: Workflow trace instance
        execution_start: Workflow start timestamp

    Returns:
        Execution summary with trace_id and dev_mode flag
    """
    logger.info("DEV_MODE enabled - running Python task only")
    python_result = await fetch_language_repos('Python')
    add_task_to_trace(python_result, trace, language='Python')
    logger.info("Python task completed, starting ETL pipeline")

    github_api, db_pool = await init_connections_with_error_handling()
    try:
        aggregate_task = trace.add_task('aggregate_results')
        final_result = await aggregate_results([python_result], db_pool, execution_start, trace)
        trace.complete_task(aggregate_task)

        execution_time = (datetime.now(timezone.utc) - execution_start).total_seconds()
        logger.info(f"DEV_MODE workflow completed in {execution_time}s")

        trace.repos_processed = final_result.get('repos_processed', 0)
        trace.complete('completed')
        await trace.persist(db_pool)

        final_result.update({
            'dev_mode': True,
            'languages': ['Python'],
            'trace_id': trace.run_id
        })
        return final_result
    finally:
        await cleanup_connections(github_api, db_pool)


async def run_production_pipeline(trace: WorkflowTrace, execution_start: datetime) -> Dict:
    """
    Run production mode pipeline (all languages + Render + ETL).

    Args:
        trace: Workflow trace instance
        execution_start: Workflow start timestamp

    Returns:
        Execution summary with trace_id
    """
    # Production mode: Full pipeline
    language_tasks = [fetch_language_repos(lang) for lang in TARGET_LANGUAGES]
    logger.info(f"Created {len(language_tasks)} language tasks for {TARGET_LANGUAGES}")

    results = await asyncio.gather(*language_tasks, fetch_render_repos(), return_exceptions=True)

    # Process results and update trace
    logger.info(f"Parallel tasks completed. Total results: {len(results)}")
    for i, result in enumerate(results):
        process_task_result(result, i, TARGET_LANGUAGES, trace)

    # Aggregate and store final results
    github_api, db_pool = await init_connections_with_error_handling()
    try:
        aggregate_task = trace.add_task('aggregate_results')
        final_result = await aggregate_results(results, db_pool, execution_start, trace)
        trace.complete_task(aggregate_task)

        trace.repos_processed = final_result.get('repos_processed', 0)
        trace.complete('completed')
        await trace.persist(db_pool)
        final_result['trace_id'] = trace.run_id
        return final_result
    finally:
        await cleanup_connections(github_api, db_pool)


@app.task
async def main_analysis_task() -> Dict:
    """
    Main orchestrator task for the entire analysis workflow.

    Spawns parallel tasks for:
    - 3 language-specific analyses (Python, TypeScript, Go)
    - 1 Render projects fetch

    Returns execution summary.
    """
    execution_start = datetime.now(timezone.utc)
    logger.info(f"Workflow started at {execution_start}")

    # Initialize workflow trace
    trace = WorkflowTrace()
    logger.info(f"Workflow trace initialized: {trace.run_id}")

    try:
        if DEV_MODE:
            result = await run_dev_mode_pipeline(trace, execution_start)
        else:
            result = await run_production_pipeline(trace, execution_start)

        return result

    except Exception as e:
        # Mark trace as failed
        trace.complete('failed', error_message=str(e))
        logger.error(f"Workflow failed: {e}")
        raise
