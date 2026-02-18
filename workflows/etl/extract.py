"""
Extract Module
Extracts validated data from staging layer for transformation.
"""

import asyncpg
import json
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
                srv.created_at,
                srv.updated_at,
                srv.readme_content
            FROM stg_repos_validated srv
            ORDER BY srv.stars DESC
        """)

        # Convert asyncpg.Record objects to dictionaries
        return [dict(repo) for repo in repos]


async def store_raw_repos(repos: List[Dict], db_pool: asyncpg.Pool,
                          source_language: str = None,
                          readme_contents: Dict[str, str] = None):
    """
    Store raw repository data in the raw layer.

    Args:
        repos: List of repository data from GitHub API
        db_pool: Database connection pool
        source_language: Programming language filter used
        readme_contents: Dictionary mapping repo full_name to README content
    """
    async with db_pool.acquire() as conn:
        for repo in repos:
            repo_name = repo.get('full_name', '')
            if not repo_name:
                continue
            readme = readme_contents.get(repo_name) if readme_contents else None
            
            await conn.execute("""
                INSERT INTO raw_github_repos
                    (repo_full_name, api_response, readme_content, source_language)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (repo_full_name) DO UPDATE SET
                    api_response = EXCLUDED.api_response,
                    readme_content = EXCLUDED.readme_content,
                    source_language = EXCLUDED.source_language,
                    fetch_timestamp = NOW()
            """, repo_name, json.dumps(repo), readme, source_language)
