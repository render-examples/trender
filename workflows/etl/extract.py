"""
Extract Module
Extracts validated data from staging layer for transformation.
"""

import asyncpg
from typing import List, Dict


async def extract_from_staging(db_pool: asyncpg.Pool) -> List[Dict]:
    """
    Extract data from staging layer tables.

    Args:
        db_pool: Database connection pool

    Returns:
        List of dictionaries containing repository data from staging
    """
    async with db_pool.acquire() as conn:
        # Extract validated repos from staging
        repos = await conn.fetch("""
            SELECT
                srv.repo_full_name,
                srv.repo_url,
                srv.language,
                srv.description,
                srv.stars,
                srv.forks,
                srv.open_issues,
                srv.created_at,
                srv.updated_at,
                srv.commits_last_7_days,
                srv.issues_closed_last_7_days,
                srv.active_contributors,
                srv.uses_render,
                srv.data_quality_score,
                sre.render_category,
                sre.render_services,
                sre.render_complexity_score,
                sre.has_blueprint_button,
                sre.service_count
            FROM stg_repos_validated srv
            LEFT JOIN stg_render_enrichment sre
                ON srv.repo_full_name = sre.repo_full_name
            WHERE srv.data_quality_score >= 0.70
            ORDER BY srv.stars DESC
        """)

        # Convert asyncpg.Record objects to dictionaries
        return [dict(repo) for repo in repos]


async def store_raw_repos(repos: List[Dict], db_pool: asyncpg.Pool,
                          source_language: str = None, source_type: str = 'trending'):
    """
    Store raw repository data in the raw layer.

    Args:
        repos: List of repository data from GitHub API
        db_pool: Database connection pool
        source_language: Programming language filter used
        source_type: Type of source ('trending' or 'render_ecosystem')
    """
    async with db_pool.acquire() as conn:
        for repo in repos:
            await conn.execute("""
                INSERT INTO raw_github_repos
                    (repo_full_name, api_response, source_language, source_type)
                VALUES ($1, $2, $3, $4)
            """, repo.get('full_name', ''), repo, source_language, source_type)


async def store_raw_metrics(repo_full_name: str, metric_type: str,
                            metric_data: Dict, db_pool: asyncpg.Pool):
    """
    Store raw metrics data in the raw layer.

    Args:
        repo_full_name: Full repository name (owner/repo)
        metric_type: Type of metric ('commits', 'issues', 'contributors')
        metric_data: Metric data from GitHub API
        db_pool: Database connection pool
    """
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO raw_repo_metrics
                (repo_full_name, metric_type, metric_data)
            VALUES ($1, $2, $3)
        """, repo_full_name, metric_type, metric_data)
