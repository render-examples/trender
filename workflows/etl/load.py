"""
Analytics layer loading functions.

This module handles loading data from staging to the analytics layer,
with un-nested operations for improved readability.
"""

import logging
from datetime import date, datetime, timezone
from typing import List, Optional
import asyncpg

from utils.scoring import calculate_momentum_score

logger = logging.getLogger(__name__)


async def upsert_dimension_repo(repo: dict, conn: asyncpg.Connection) -> Optional[int]:
    """
    Upsert repository into dim_repositories and return repo_key.

    Args:
        repo: Repository record from staging
        conn: Database connection

    Returns:
        repo_key if successful, None otherwise
    """
    repo_name = repo['repo_full_name']
    if not repo_name:
        return None

    try:
        # Upsert into dim_repositories (simplified, no SCD Type 2)
        await conn.execute("""
            INSERT INTO dim_repositories
                (repo_full_name, repo_url, description, readme_content, language,
                 created_at, render_category, valid_from, is_current)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), TRUE)
            ON CONFLICT (repo_full_name)
            WHERE is_current = TRUE
            DO UPDATE SET
                repo_url = EXCLUDED.repo_url,
                description = EXCLUDED.description,
                readme_content = EXCLUDED.readme_content
        """, repo_name, repo['repo_url'], repo['description'],
            repo['readme_content'], repo['language'], repo['created_at'],
            'community')

        # Get repo_key
        repo_key = await conn.fetchval("""
            SELECT repo_key FROM dim_repositories
            WHERE repo_full_name = $1 AND is_current = TRUE
        """, repo_name)

        if not repo_key:
            logger.warning(f"Missing repo_key for {repo_name}, skipping")
            return None

        return repo_key

    except Exception as e:
        logger.error(f"Error upserting dimension for {repo_name}: {type(e).__name__}: {e}")
        return None


async def get_language_key(language: str, conn: asyncpg.Connection) -> Optional[int]:
    """
    Get language_key from dim_languages.

    Args:
        language: Language name
        conn: Database connection

    Returns:
        language_key if found, None otherwise
    """
    language_key = await conn.fetchval("""
        SELECT language_key FROM dim_languages
        WHERE language_name = $1
    """, language)

    if not language_key:
        logger.error(f"Language '{language}' not found in dim_languages. Expected one of: Python, TypeScript, Go, render")
        return None

    return language_key


async def insert_fact_snapshot(
    repo_key: int,
    language_key: int,
    repo: dict,
    today: date,
    momentum_score: float,
    rank_overall: int,
    conn: asyncpg.Connection
) -> bool:
    """
    Insert fact snapshot with calculated momentum score.

    Args:
        repo_key: Repository key
        language_key: Language key
        repo: Repository record
        today: Snapshot date
        momentum_score: Calculated momentum score
        rank_overall: Overall rank
        conn: Database connection

    Returns:
        True if successful, False otherwise
    """
    try:
        await conn.execute("""
            INSERT INTO fact_repo_snapshots
                (repo_key, language_key, snapshot_date, stars,
                 star_velocity, activity_score, momentum_score,
                 rank_overall, rank_in_language)
            VALUES ($1, $2, $3, $4, 0, 0, $5, $6, NULL)
            ON CONFLICT (repo_key, snapshot_date) DO UPDATE SET
                stars = EXCLUDED.stars,
                momentum_score = EXCLUDED.momentum_score,
                rank_overall = EXCLUDED.rank_overall
        """, repo_key, language_key, today, repo['stars'], momentum_score, rank_overall)
        return True
    except Exception as e:
        logger.error(f"Error inserting fact snapshot: {type(e).__name__}: {e}")
        return False


async def load_single_repo(
    repo: dict,
    idx: int,
    today: date,
    now: datetime,
    max_stars_general: int,
    max_stars_render: int,
    conn: asyncpg.Connection
) -> bool:
    """
    Load a single repository to analytics layer.

    This orchestrates the per-repo operations with reduced nesting.

    Args:
        repo: Repository record from staging
        idx: Repository index for ranking
        today: Snapshot date
        now: Current datetime
        max_stars_general: Max stars for general repos
        max_stars_render: Max stars for render repos
        conn: Database connection

    Returns:
        True if successful, False otherwise
    """
    repo_name = repo['repo_full_name']

    # Upsert dimension
    repo_key = await upsert_dimension_repo(repo, conn)
    if not repo_key:
        return False

    # Get language key
    language_key = await get_language_key(repo['language'], conn)
    if not language_key:
        return False

    # Calculate momentum score
    stars = repo.get('stars', 0)
    is_render = repo.get('language') == 'render'

    # Normalize stars based on appropriate max (general vs render)
    max_stars = max_stars_render if is_render else max_stars_general

    momentum_score = calculate_momentum_score(
        stars=stars,
        created_at=repo.get('created_at'),
        now=now,
        max_stars=max_stars,
        recency_weight=0.7,
        stars_weight=0.3
    )

    normalized_stars = stars / max_stars if max_stars > 0 else 0.0

    logger.info(f"Score for {repo_name}: stars={stars}, norm_stars={normalized_stars:.3f}, momentum={momentum_score:.3f}")

    # Insert fact snapshot
    success = await insert_fact_snapshot(
        repo_key, language_key, repo, today, momentum_score, idx, conn
    )
    if not success:
        return False

    return True


async def load_to_analytics_simple(repos: List, conn: asyncpg.Connection):
    """
    Simplified load: upsert dimensions and facts with recency-weighted scoring.

    Scoring formula (heavily favors recent repos):
    - 70% recency score (exponential decay based on repo creation date)
    - 30% normalized star count

    This prioritizes emerging/trending projects over established popular repos.

    Args:
        repos: List of repository records from staging
        conn: Database connection
    """
    today = date.today()
    now = datetime.now(timezone.utc)

    # Calculate max stars for normalization (separately for general and Render repos)
    general_repos = [r for r in repos if r.get('language') != 'render']
    render_repos = [r for r in repos if r.get('language') == 'render']

    max_stars_general = max([r.get('stars', 1) for r in general_repos]) if general_repos else 1
    max_stars_render = max([r.get('stars', 1) for r in render_repos]) if render_repos else 1

    logger.info(f"Max stars - General: {max_stars_general}, Render: {max_stars_render}")

    # Load each repo
    success_count = 0
    for idx, repo in enumerate(repos, 1):
        repo_name = repo.get('repo_full_name')
        if not repo_name:
            continue

        success = await load_single_repo(
            repo, idx, today, now,
            max_stars_general, max_stars_render,
            conn
        )
        if success:
            success_count += 1

    logger.info(f"Loaded {success_count}/{len(repos)} repos to analytics layer")
