"""
Load Module
Loads transformed data into analytics layer (fact and dimension tables).
"""

import asyncpg
from typing import List, Dict
from datetime import datetime, date


async def load_to_analytics(repos: List[Dict], db_pool: asyncpg.Pool):
    """
    Load transformed data into analytics layer.

    Args:
        repos: List of transformed and ranked repository dictionaries
        db_pool: Database connection pool
    """
    async with db_pool.acquire() as conn:
        # Start a transaction
        async with conn.transaction():
            # Upsert into dim_repositories (SCD Type 2)
            await upsert_dim_repositories(repos, conn)

            # Insert daily snapshots into fact_repo_snapshots
            await insert_fact_snapshots(repos, conn)

            # Insert Render usage into fact_render_usage
            render_repos = [r for r in repos if r.get('uses_render')]
            await insert_render_usage(render_repos, conn)


async def upsert_dim_repositories(repos: List[Dict], conn: asyncpg.Connection):
    """
    Upsert repositories into dimension table with SCD Type 2 logic.

    Args:
        repos: List of repository dictionaries
        conn: Database connection
    """
    for repo in repos:
        repo_name = repo.get('repo_full_name')
        if not repo_name:
            continue

        # Check if repo exists and if data has changed
        existing = await conn.fetchrow("""
            SELECT repo_key, description, readme_content, uses_render, render_category
            FROM dim_repositories
            WHERE repo_full_name = $1 AND is_current = TRUE
        """, repo_name)

        needs_update = False
        if existing:
            # Check if significant fields have changed
            if (existing['description'] != repo.get('description') or
                existing['readme_content'] != repo.get('readme_content') or
                existing['uses_render'] != repo.get('uses_render') or
                existing['render_category'] != repo.get('render_category')):
                needs_update = True

        if existing and needs_update:
            # Close out the old record (SCD Type 2)
            await conn.execute("""
                UPDATE dim_repositories
                SET valid_to = NOW(), is_current = FALSE
                WHERE repo_key = $1
            """, existing['repo_key'])

            # Insert new record
            await conn.execute("""
                INSERT INTO dim_repositories
                    (repo_full_name, repo_url, description, readme_content, language, created_at,
                     uses_render, render_category, valid_from, is_current)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), TRUE)
            """, repo_name, repo.get('repo_url'), repo.get('description'),
                repo.get('readme_content'), repo.get('language'), repo.get('created_at'),
                repo.get('uses_render', False), repo.get('render_category'))

        elif not existing:
            # Insert new record
            await conn.execute("""
                INSERT INTO dim_repositories
                    (repo_full_name, repo_url, description, readme_content, language, created_at,
                     uses_render, render_category, valid_from, is_current)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), TRUE)
            """, repo_name, repo.get('repo_url'), repo.get('description'),
                repo.get('readme_content'), repo.get('language'), repo.get('created_at'),
                repo.get('uses_render', False), repo.get('render_category'))


async def insert_fact_snapshots(repos: List[Dict], conn: asyncpg.Connection):
    """
    Insert daily snapshots into fact table.

    Args:
        repos: List of repository dictionaries
        conn: Database connection
    """
    today = date.today()

    for repo in repos:
        repo_name = repo.get('repo_full_name')
        if not repo_name:
            continue

        # Get repo_key and language_key
        repo_data = await conn.fetchrow("""
            SELECT dr.repo_key, dl.language_key
            FROM dim_repositories dr
            JOIN dim_languages dl ON dr.language = dl.language_name
            WHERE dr.repo_full_name = $1 AND dr.is_current = TRUE
        """, repo_name)

        if not repo_data:
            continue

        # Insert or update snapshot
        await conn.execute("""
            INSERT INTO fact_repo_snapshots
                (repo_key, language_key, snapshot_date, stars, forks, star_velocity,
                 activity_score, momentum_score, commits_last_7_days,
                 issues_closed_last_7_days, active_contributors,
                 rank_overall, rank_in_language)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (repo_key, snapshot_date) DO UPDATE SET
                stars = EXCLUDED.stars,
                forks = EXCLUDED.forks,
                star_velocity = EXCLUDED.star_velocity,
                activity_score = EXCLUDED.activity_score,
                momentum_score = EXCLUDED.momentum_score,
                commits_last_7_days = EXCLUDED.commits_last_7_days,
                issues_closed_last_7_days = EXCLUDED.issues_closed_last_7_days,
                active_contributors = EXCLUDED.active_contributors,
                rank_overall = EXCLUDED.rank_overall,
                rank_in_language = EXCLUDED.rank_in_language
        """, repo_data['repo_key'], repo_data['language_key'], today,
            repo.get('stars', 0), repo.get('forks', 0),
            repo.get('star_velocity', 0), repo.get('activity_score', 0),
            repo.get('momentum_score', 0), repo.get('commits_last_7_days', 0),
            repo.get('issues_closed_last_7_days', 0),
            repo.get('active_contributors', 0),
            repo.get('rank_overall'), repo.get('rank_in_language'))


async def insert_render_usage(render_repos: List[Dict], conn: asyncpg.Connection):
    """
    Insert Render usage data into fact table.

    Args:
        render_repos: List of Render-enabled repository dictionaries
        conn: Database connection
    """
    today = date.today()

    for repo in render_repos:
        repo_name = repo.get('repo_full_name')
        if not repo_name:
            continue

        # Get repo_key
        repo_key = await conn.fetchval("""
            SELECT repo_key FROM dim_repositories
            WHERE repo_full_name = $1 AND is_current = TRUE
        """, repo_name)

        if not repo_key:
            continue

        # Get render services if available
        render_services = repo.get('render_services', [])
        if not render_services or not isinstance(render_services, list):
            render_services = []

        # Insert usage for each service type
        for service_type in render_services:
            service_key = await conn.fetchval("""
                SELECT service_key FROM dim_render_services
                WHERE service_type = $1
            """, service_type)

            if service_key:
                await conn.execute("""
                    INSERT INTO fact_render_usage
                        (repo_key, service_key, snapshot_date, service_count,
                         complexity_score, has_blueprint)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT DO NOTHING
                """, repo_key, service_key, today,
                    repo.get('service_count', 1),
                    repo.get('render_complexity_score'),
                    repo.get('has_blueprint_button', False))
