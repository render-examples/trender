"""
Language-specific and Render repository fetching tasks.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import asyncpg

from app import app
from connections import init_connections, cleanup_connections
from github_api import GitHubAPIClient
from utils import init_connections_with_error_handling, fetch_readmes_parallel
from etl import store_raw_repos
from tasks.batch_analysis import analyze_repo_batch

logger = logging.getLogger(__name__)

# Development mode - set to limit processing for faster iteration
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'
DEV_REPO_LIMIT = int(os.getenv('DEV_REPO_LIMIT', '50'))


@app.task
async def fetch_language_repos(language: str) -> Dict:
    """
    Fetch and store trending repos for a specific language.

    Args:
        language: Programming language to fetch

    Returns:
        Dict with structure:
        {
            'repos': List of enriched repository dictionaries,
            'subtasks': List of timing metadata from subtasks,
            'started_at': ISO timestamp string,
            'completed_at': ISO timestamp string
        }
    """
    start_time = datetime.now(timezone.utc)
    logger.info(f"Fetching {language} repositories")

    # Initialize connections for this task
    github_api, db_pool = await init_connections_with_error_handling()

    try:
        # Search GitHub API (API now filters out repos without language)
        try:
            repos = await github_api.search_repositories(
                language=language,
                sort='stars',
                updated_since=datetime.now(timezone.utc) - timedelta(days=30),
                created_since=datetime.now(timezone.utc) - timedelta(days=180)
            )
            logger.info(f"GitHub API returned {len(repos)} repos for {language} (updated in last 30d, created in last 180d, all with valid language)")
        except Exception as e:
            logger.error(f"search_repositories failed for {language}: {type(e).__name__}: {e}")
            raise

        # Target: 25 repos per language (or DEV_REPO_LIMIT in dev mode)
        target_count = DEV_REPO_LIMIT if DEV_MODE else 25

        # Take up to target_count repos
        repos_to_process = repos[:target_count]
        logger.info(f"Processing {len(repos_to_process)} repos for {language} (target={target_count}, DEV_MODE={DEV_MODE})")

        if not repos_to_process:
            logger.warning(f"No repos found for {language}")
            return {
                'repos': [],
                'subtasks': []
            }

        # Fetch READMEs in parallel (much faster!)
        readme_contents = await fetch_readmes_parallel(repos_to_process, github_api)
        logger.info(f"Fetched {len(readme_contents)} READMEs for {language}")

        # Store raw API responses with READMEs
        await store_raw_repos(repos_to_process, db_pool, source_language=language, readme_contents=readme_contents)

        # Spawn batch analysis task (subtask initializes its own connections)
        # Pass README contents to avoid duplicate API calls
        batch_results = await analyze_repo_batch(repos_to_process, readme_contents)

        end_time = datetime.now(timezone.utc)
        logger.info(f"Fetched {len(batch_results['enriched_repos'])} {language} repos")
        return {
            'repos': batch_results['enriched_repos'],
            'subtasks': [batch_results['timing']],
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat()
        }
    finally:
        # Cleanup connections
        await cleanup_connections(github_api, db_pool)


@app.task
async def fetch_render_repos() -> Dict:
    """
    Fetch independent Render projects using code search.
    Searches for repositories with render.yaml in root directory.
    All repos are assigned language='render' (lowercase) for identification.

    Returns:
        Dict with structure:
        {
            'repos': List of repository dictionaries,
            'subtasks': List of timing metadata from subtasks,
            'started_at': ISO timestamp string,
            'completed_at': ISO timestamp string
        }
    """
    start_time = datetime.now(timezone.utc)
    logger.info("Searching for render.yaml repositories")

    # Initialize connections
    github_api, db_pool = await init_connections_with_error_handling()

    try:
        # Code search for render.yaml in root directory
        # API assigns language='render' (lowercase) to all repos automatically
        # Request 100 initially to ensure we get 25+ repos
        # Filter for repos created within last 18 months
        eighteen_months_ago = datetime.now(timezone.utc) - timedelta(days=548)  # 18 months ≈ 548 days
        repos = await github_api.search_render_projects(limit=100, created_since=eighteen_months_ago)
        logger.info(f"Found {len(repos)} repos with render.yaml in root (all with language='render')")

        if not repos:
            logger.warning("No Render projects found via code search")
            return {
                'repos': [],
                'subtasks': []
            }

        # Target: 25 render projects
        target_count = 25
        repos_to_process = repos[:target_count]
        logger.info(f"Processing {len(repos_to_process)} render projects (target={target_count})")

        # Fetch READMEs in parallel (same as language repos)
        readme_contents = await fetch_readmes_parallel(repos_to_process, github_api)
        logger.info(f"Fetched {len(readme_contents)} READMEs for render repos")

        # Store in raw layer with READMEs
        await store_raw_repos(repos_to_process, db_pool, source_language='render', readme_contents=readme_contents)

        # Analyze batch (stores in staging) with README contents
        analyzed = await analyze_repo_batch(repos_to_process, readme_contents)

        end_time = datetime.now(timezone.utc)
        logger.info(f"Found {len(analyzed['enriched_repos'])} Render repos")
        return {
            'repos': analyzed['enriched_repos'],
            'subtasks': [analyzed['timing']],
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat()
        }

    finally:
        await cleanup_connections(github_api, db_pool)
