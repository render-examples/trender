"""
Helper utility functions for workflow execution.
"""

import sys
import logging
from typing import List, Tuple
import asyncpg

from connections import init_connections
from github_api import GitHubAPIClient

logger = logging.getLogger(__name__)


def chunk_list(items: List, size: int) -> List[List]:
    """Split a list into chunks of specified size."""
    return [items[i:i + size] for i in range(0, len(items), size)]


async def init_connections_with_error_handling() -> Tuple[GitHubAPIClient, asyncpg.Pool]:
    """
    Initialize connections with consistent error handling.

    Returns:
        Tuple of (GitHubAPIClient, asyncpg.Pool)

    Raises:
        SystemExit: If connection fails (exits gracefully with status 1)
    """
    try:
        return await init_connections()
    except ConnectionError as e:
        logger.error(f"FATAL: Cannot connect to database: {e}")
        logger.error("Exiting workflow gracefully due to connection failure")
        sys.exit(1)
