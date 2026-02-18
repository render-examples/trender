"""
Result aggregation and ETL orchestration.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import asyncpg

from etl.load import load_to_analytics_simple
from etl.cleanup import cleanup_old_data

logger = logging.getLogger(__name__)


async def aggregate_results(
    all_results: List,
    db_pool: asyncpg.Pool,
    execution_start: datetime,
    trace: Optional = None
) -> Dict:
    """
    Simplified ETL: Extract from staging, order by stars, load to analytics.

    Args:
        all_results: List of results from parallel tasks
        db_pool: Database connection pool
        execution_start: Workflow execution start time
        trace: Optional workflow trace for tracking cleanup task

    Returns:
        Execution summary dictionary
    """
    logger.info("Aggregating results from all tasks")

    # Count successful task results
    # Results are now dicts with 'repos' key, or Exceptions, or empty dicts
    successful_tasks = sum(
        1 for r in all_results
        if not isinstance(r, Exception) and isinstance(r, dict) and len(r.get('repos', [])) > 0
    )
    logger.info(f"Successful tasks: {successful_tasks}/{len(all_results)}")

    async with db_pool.acquire() as conn:
        # Extract repos in two parts:
        # 1. Top trending repos per language (balanced across Python, TypeScript, Go)
        # 2. ALL qualifying Render repos (language='render')

        # Part 1: Top 50 repos per language for balanced representation
        general_repos = await conn.fetch("""
            WITH ranked_repos AS (
                SELECT
                    srv.repo_full_name,
                    srv.repo_url,
                    srv.language,
                    srv.description,
                    srv.stars,
                    srv.created_at,
                    srv.updated_at,
                    srv.readme_content,
                    ROW_NUMBER() OVER (PARTITION BY srv.language ORDER BY srv.stars DESC) as lang_rank
                FROM stg_repos_validated srv
            )
            SELECT
                repo_full_name,
                repo_url,
                language,
                description,
                stars,
                created_at,
                updated_at,
                readme_content
            FROM ranked_repos
            WHERE lang_rank <= 50
            ORDER BY stars DESC
        """)

        # Part 2: ALL Render repos (identified by language='render')
        render_repos = await conn.fetch("""
            SELECT
                srv.repo_full_name,
                srv.repo_url,
                srv.language,
                srv.description,
                srv.stars,
                srv.created_at,
                srv.updated_at,
                srv.readme_content
            FROM stg_repos_validated srv
            WHERE srv.language = 'render'
            ORDER BY srv.stars DESC
        """)

        # Merge repos (deduplicate by repo_full_name)
        seen_repos = set()
        repos = []

        for repo in list(general_repos) + list(render_repos):
            repo_name = repo.get('repo_full_name')
            if repo_name not in seen_repos:
                seen_repos.add(repo_name)
                repos.append(repo)

        logger.info(f"Extracted {len(general_repos)} general + {len(render_repos)} render repos = {len(repos)} total (deduplicated) from staging")

        if not repos:
            logger.warning("No repos found in staging for analytics")
            return {
                'repos_processed': 0,
                'execution_time': (datetime.now(timezone.utc) - execution_start).total_seconds(),
                'success': True
            }

        # Load to analytics (consolidated logic)
        await load_to_analytics_simple(repos, conn)

        # Run data retention cleanup after successful ETL
        # Note: Cleanup errors are logged but don't fail the workflow
        # This ensures ETL success even if cleanup encounters issues
        logger.info("ETL completed successfully, running data retention cleanup...")

        # Track cleanup task if trace is available
        cleanup_task = None
        if trace:
            cleanup_task = trace.add_task('cleanup_old_data')

        cleanup_stats = await cleanup_old_data(db_pool)

        if cleanup_task:
            # Mark as completed even if cleanup had errors (graceful degradation)
            status = 'completed' if 'error' not in cleanup_stats else 'failed'
            trace.complete_task(cleanup_task, status)

        # Log warning if cleanup failed but continue workflow
        if 'error' in cleanup_stats:
            logger.warning(f"Data cleanup encountered an error but workflow continues: {cleanup_stats['error']}")

        return {
            'repos_processed': len(repos),
            'execution_time': (datetime.now(timezone.utc) - execution_start).total_seconds(),
            'cleanup_stats': cleanup_stats,
            'success': True
        }
