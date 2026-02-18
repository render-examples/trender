"""
Data retention and cleanup operations.
"""

import os
import logging
from typing import Dict
import asyncpg

logger = logging.getLogger(__name__)


async def store_in_staging(repo: Dict, db_pool: asyncpg.Pool):
    """Store enriched repository data in staging layer."""
    description = repo.get('description')
    readme = repo.get('readme_content')
    if description:
        description = description.replace('\x00', '')
    if readme:
        readme = readme.replace('\x00', '')
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO stg_repos_validated
                (repo_full_name, repo_url, language, description, stars,
                 created_at, updated_at, readme_content)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (repo_full_name) DO UPDATE SET
                stars = EXCLUDED.stars,
                updated_at = EXCLUDED.updated_at,
                readme_content = EXCLUDED.readme_content,
                loaded_at = NOW()
        """, repo.get('repo_full_name'), repo.get('repo_url'), repo.get('language'),
            description, repo.get('stars', 0),
            repo.get('created_at'), repo.get('updated_at'),
            readme)


async def cleanup_old_data(db_pool: asyncpg.Pool) -> Dict[str, int]:
    """
    Execute tiered data retention cleanup.

    Retention policy:
    - Raw layer: 7 days (debugging and reprocessing)
    - Staging layer: 7 days (ETL audit trail)
    - Analytics layer: 30 days (trending analysis)

    Args:
        db_pool: Database connection pool

    Returns:
        Dictionary with cleanup statistics per table
    """
    logger.info("Starting data retention cleanup...")

    # Read SQL cleanup script
    script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'data_retention_cleanup.sql')

    try:
        with open(script_path, 'r') as f:
            cleanup_sql = f.read()
    except FileNotFoundError:
        logger.error(f"Cleanup script not found at {script_path}")
        return {'error': 'Script not found'}
    except IOError as e:
        logger.error(f"Failed to read cleanup script: {e}")
        return {'error': f'Failed to read script: {str(e)}'}

    cleanup_stats = {}

    try:
        async with db_pool.acquire() as conn:
            # Execute cleanup script
            # Note: The script uses a transaction, so it's atomic
            # Use execute() instead of fetch() to support multi-statement scripts
            await conn.execute(cleanup_sql)

            # Query row counts after cleanup
            tables = [
                'raw_github_repos',
                'stg_repos_validated',
                'fact_repo_snapshots'
            ]

            for table in tables:
                try:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    cleanup_stats[table] = count
                    logger.info(f"  {table}: {count} rows remaining")
                except Exception as e:
                    logger.warning(f"  {table}: Could not get count ({e})")

        logger.info("Data retention cleanup completed successfully")
        return cleanup_stats

    except asyncpg.PostgresError as e:
        logger.error(f"Database error during data retention cleanup: {type(e).__name__}: {str(e)}")
        logger.error(f"SQL State: {e.sqlstate if hasattr(e, 'sqlstate') else 'N/A'}")
        # Return error but don't fail the workflow
        return {'error': f'Database error: {str(e)}'}
    except Exception as e:
        logger.error(f"Error during data retention cleanup: {type(e).__name__}: {str(e)}", exc_info=True)
        # Return error but don't fail the workflow
        return {'error': str(e)}
