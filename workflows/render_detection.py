"""
Render Detection Module
Simplified: Repos found via code search are trusted to use Render.
No need to fetch/parse render.yaml again.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


async def store_render_enrichment(enriched_projects: List[Dict], db_pool):
    """
    Store Render enrichment data in staging layer.

    Args:
        enriched_projects: List of enriched project dictionaries
        db_pool: Database connection pool
    """
    async with db_pool.acquire() as conn:
        for project in enriched_projects:
            repo_name = project.get('repo_full_name')
            if not repo_name:
                continue

            await conn.execute("""
                INSERT INTO stg_render_enrichment
                    (repo_full_name, render_category, render_services,
                     has_blueprint_button, render_complexity_score,
                     service_count)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (repo_full_name) DO UPDATE SET
                    render_category = EXCLUDED.render_category,
                    render_services = EXCLUDED.render_services,
                    has_blueprint_button = EXCLUDED.has_blueprint_button,
                    render_complexity_score = EXCLUDED.render_complexity_score,
                    service_count = EXCLUDED.service_count,
                    loaded_at = NOW()
            """, repo_name, project.get('render_category'),
                project.get('render_services', []),
                project.get('has_blueprint_button', False),
                project.get('render_complexity_score'),
                project.get('service_count', 0))
