"""
Task result processing utilities for workflow execution.

This module handles task result processing and trace updates,
with un-nested conditional logic for improved readability.
"""

import logging
import traceback
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def determine_task_info(index: int, target_languages: List[str]) -> tuple[str, Optional[str]]:
    """
    Determine task name and language from task index.

    Args:
        index: Task result index
        target_languages: List of target language names

    Returns:
        Tuple of (task_name, language) where language is None for non-language tasks
    """
    is_language_task = index < len(target_languages)
    task_name = target_languages[index] if is_language_task else 'fetch_render_repos'
    language = task_name if is_language_task else None
    return task_name, language


def handle_exception_result(result: Exception, task_name: str, language: Optional[str], trace) -> None:
    """
    Handle exception results from task execution.

    Args:
        result: Exception object
        task_name: Name of the failed task
        language: Language name (if applicable)
        trace: WorkflowTrace instance
    """
    logger.error(f"Task ({task_name}) FAILED: {type(result).__name__}: {str(result)}")
    logger.error("".join(traceback.format_exception(type(result), result, result.__traceback__)))

    task_ref = trace.add_task(
        'fetch_language_repos' if language else 'fetch_render_repos',
        language=language
    )
    trace.complete_task(task_ref, 'failed')


def add_subtasks_to_trace(task_ref: Dict, subtasks: List[Dict], trace) -> None:
    """
    Add subtask timing information to the trace tree.

    Args:
        task_ref: Parent task reference in trace
        subtasks: List of subtask timing dictionaries
        trace: WorkflowTrace instance
    """
    for subtask_timing in subtasks:
        subtask = trace.add_subtask(task_ref, subtask_timing['task_name'])
        subtask['started_at'] = subtask_timing['started_at']
        subtask['completed_at'] = subtask_timing['completed_at']
        subtask['status'] = subtask_timing['status']


def handle_success_result(result: Dict, task_name: str, language: Optional[str], trace) -> None:
    """
    Handle successful task results.

    Args:
        result: Task result dictionary
        task_name: Name of the completed task
        language: Language name (if applicable)
        trace: WorkflowTrace instance
    """
    result_len = len(result.get('repos', [])) if isinstance(result, dict) else 'N/A'
    logger.info(f"Task ({task_name}) SUCCESS: {type(result).__name__}, items={result_len}")

    if not isinstance(result, dict):
        return

    task_ref = trace.add_task(
        'fetch_language_repos' if language else 'fetch_render_repos',
        language=language
    )
    task_ref['started_at'] = result.get('started_at', task_ref['started_at'])
    task_ref['completed_at'] = result.get('completed_at')
    task_ref['status'] = 'completed'

    # Add subtasks from the result to the trace
    subtasks = result.get('subtasks', [])
    if subtasks:
        add_subtasks_to_trace(task_ref, subtasks, trace)


def process_task_result(result, index: int, target_languages: List[str], trace) -> None:
    """
    Process a single task result and update trace.

    This is the main entry point for result processing, with un-nested
    conditional logic delegated to helper functions.

    Args:
        result: Task result (dict or Exception)
        index: Task result index
        target_languages: List of target language names
        trace: WorkflowTrace instance
    """
    # Determine task info
    task_name, language = determine_task_info(index, target_languages)

    # Handle exceptions
    if isinstance(result, Exception):
        handle_exception_result(result, task_name, language, trace)
        return

    # Handle successful results
    handle_success_result(result, task_name, language, trace)


def add_task_to_trace(result: Dict, trace, language: Optional[str] = None) -> None:
    """
    Add a completed task and its subtasks to the trace.

    This is a simplified version for direct task addition without index-based lookup.

    Args:
        result: Task result dictionary
        trace: WorkflowTrace instance
        language: Language name (if applicable)
    """
    task_ref = trace.add_task('fetch_language_repos', language=language)
    task_ref['started_at'] = result.get('started_at', task_ref['started_at'])
    task_ref['completed_at'] = result.get('completed_at')
    task_ref['status'] = 'completed'

    subtasks = result.get('subtasks', [])
    if subtasks:
        add_subtasks_to_trace(task_ref, subtasks, trace)
