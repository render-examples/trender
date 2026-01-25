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
                srv.readme_content,
                sre.render_category,
                sre.render_services,
                sre.render_complexity_score,
                sre.has_blueprint_button,
                sre.service_count
            FROM stg_repos_validated srv
            LEFT JOIN stg_render_enrichment sre
                ON srv.repo_full_name = sre.repo_full_name
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
    # #region agent log
    import time
    debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
    json_str = json.dumps(metric_data)
    payload_size_bytes = len(json_str.encode('utf-8'))
    item_count = metric_data.get('count', 0)
    
    start_time = time.time()
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"extract.py:89","message":"store_raw_metrics ENTRY","data":{"repo":repo_full_name,"metric_type":metric_type,"item_count":item_count,"payload_size_bytes":payload_size_bytes,"pool_size":db_pool.get_size(),"pool_free":db_pool.get_size()-db_pool.get_idle_size()},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H1,H2"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    # #region agent log
    acquire_start = time.time()
    # #endregion
    
    async with db_pool.acquire() as conn:
        # #region agent log
        acquire_time = time.time() - acquire_start
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"extract.py:101","message":"DB connection acquired","data":{"repo":repo_full_name,"metric_type":metric_type,"acquire_time_ms":int(acquire_time*1000)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H2,H5"}) + '\n')
        except Exception:
            pass
        # #endregion
        
        # #region agent log
        execute_start = time.time()
        # #endregion
        
        await conn.execute("""
            INSERT INTO raw_repo_metrics
                (repo_full_name, metric_type, metric_data)
            VALUES ($1, $2, $3)
            ON CONFLICT (repo_full_name, metric_type) DO UPDATE SET
                metric_data = EXCLUDED.metric_data,
                fetch_timestamp = NOW()
        """, repo_full_name, metric_type, json_str)
        
        # #region agent log
        execute_time = time.time() - execute_start
        total_time = time.time() - start_time
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"extract.py:108","message":"store_raw_metrics EXIT","data":{"repo":repo_full_name,"metric_type":metric_type,"execute_time_ms":int(execute_time*1000),"total_time_ms":int(total_time*1000)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H3,H5"}) + '\n')
        except Exception:
            pass
        # #endregion
