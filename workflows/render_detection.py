"""
Render Detection Module
Detects Render usage patterns and categorizes Render projects.
"""

import re
import yaml
import logging
from typing import Dict, List, Optional
import os

logger = logging.getLogger(__name__)


def parse_render_yaml(render_yaml_content: str) -> Dict:
    """
    Parse render.yaml configuration.

    Args:
        render_yaml_content: Content of render.yaml file

    Returns:
        Parsed configuration dictionary
    """
    # #region agent log
    import json
    import time
    debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"render_detection.py:15","message":"parse_render_yaml ENTRY","data":{"content_length":len(render_yaml_content) if render_yaml_content else 0,"content_preview":render_yaml_content[:100] if render_yaml_content else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H6"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    try:
        config = yaml.safe_load(render_yaml_content)
        if not config:
            return {}

        # Extract services
        services = config.get('services', [])
        databases = config.get('databases', [])

        parsed = {
            'services': [],
            'databases': [],
            'service_count': len(services) + len(databases)
        }

        # Parse services
        for service in services:
            service_type = service.get('type', 'unknown')
            parsed['services'].append(service_type)

        # Parse databases
        for db in databases:
            db_type = db.get('type', 'postgres')
            parsed['databases'].append(db_type)

        return parsed
    except Exception as e:
        # #region agent log
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"render_detection.py:51","message":"parse_render_yaml EXCEPTION","data":{"error_type":type(e).__name__,"error_msg":str(e)[:300],"content_sample":render_yaml_content[:200] if render_yaml_content else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H6"}) + '\n')
        except Exception:
            pass
        # #endregion
        return {}


def scan_dockerfile_for_render(dockerfile_content: str) -> Dict:
    """
    Scan Dockerfile for Render patterns.

    Args:
        dockerfile_content: Content of Dockerfile

    Returns:
        Dictionary of detected patterns
    """
    if not dockerfile_content:
        return {}

    patterns = {
        'uses_render_env': False,
        'render_specific_commands': []
    }

    # Check for RENDER environment variable
    if 'RENDER' in dockerfile_content:
        patterns['uses_render_env'] = True

    # Check for Render-specific patterns
    render_patterns = [
        r'render\.com',
        r'RENDER_.*',
        r'onrender\.com'
    ]

    for pattern in render_patterns:
        if re.search(pattern, dockerfile_content, re.IGNORECASE):
            patterns['render_specific_commands'].append(pattern)

    return patterns


def calculate_render_complexity(render_config: Dict, docker_patterns: Dict) -> int:
    """
    Calculate Render complexity score (0-10).

    Based on:
    - Number of services (0-5 points)
    - Service type diversity (0-3 points)
    - Custom configuration (0-2 points)

    Args:
        render_config: Parsed render.yaml configuration
        docker_patterns: Docker patterns detected

    Returns:
        Complexity score between 0 and 10
    """
    score = 0

    # Service count (up to 5 points)
    service_count = render_config.get('service_count', 0)
    score += min(service_count, 5)

    # Service diversity (up to 3 points)
    services = render_config.get('services', [])
    unique_services = len(set(services))
    score += min(unique_services, 3)

    # Docker customization (up to 2 points)
    if docker_patterns.get('uses_render_env'):
        score += 1
    if docker_patterns.get('render_specific_commands'):
        score += 1

    return min(score, 10)


def categorize_render_project(repo_data: Dict) -> str:
    """
    Categorize Render project based on repository metadata.

    Categories:
    - 'official': Render official repositories
    - 'employee': Render employee projects
    - 'blueprint': Render blueprint repositories
    - 'community': Community projects

    Args:
        repo_data: Repository data dictionary

    Returns:
        Category string
    """
    repo_full_name = repo_data.get('repo_full_name', '')
    owner = repo_full_name.split('/')[0] if '/' in repo_full_name else ''

    # Official Render organizations
    official_orgs = ['render-examples', 'render']
    if owner.lower() in official_orgs:
        return 'official'

    # Check for blueprint indicators
    topics = repo_data.get('topics', [])
    if isinstance(topics, list):
        if 'render-blueprints' in topics or 'render-blueprint' in topics:
            return 'blueprint'

    # Check for employee projects (would need employee list)
    employee_orgs = os.getenv('RENDER_EMPLOYEE_GITHUB_ORGS', '').split(',')
    if owner.lower() in [org.strip().lower() for org in employee_orgs if org.strip()]:
        return 'employee'

    # Default to community
    return 'community'


def score_blueprint_quality(render_data: Dict) -> int:
    """
    Score blueprint quality (0-10).

    Based on:
    - Has render.yaml (required)
    - Service diversity
    - Documentation quality
    - Deploy button presence

    Args:
        render_data: Render detection data

    Returns:
        Quality score between 0 and 10
    """
    if not render_data.get('uses_render'):
        return 0

    score = 0

    # Has render.yaml (3 points)
    if render_data.get('uses_render'):
        score += 3

    # Service count (up to 3 points)
    services = render_data.get('services', [])
    score += min(len(services), 3)

    # Service diversity (2 points)
    if len(set(services)) > 1:
        score += 2

    # Complexity (2 points)
    complexity = render_data.get('complexity_score', 0)
    if complexity >= 5:
        score += 2

    return min(score, 10)


def score_documentation(repo_data: Dict, render_data: Dict) -> int:
    """
    Score documentation quality (0-10).

    Args:
        repo_data: Repository data
        render_data: Render detection data

    Returns:
        Documentation score between 0 and 10
    """
    score = 0

    # Has description (2 points)
    if repo_data.get('description'):
        score += 2

    # Has README (3 points) - assumed if repo exists
    score += 3

    # README mentions Render (2 points)
    readme_content = repo_data.get('readme_content', '')
    if 'render' in readme_content.lower():
        score += 2

    # Has deploy button (3 points)
    if render_data.get('has_blueprint_button'):
        score += 3

    return min(score, 10)


async def detect_render_usage(repo_data: Dict, github_api, db_pool) -> Dict:
    """
    Detect Render usage by fetching and parsing render.yaml file.
    Returns comprehensive Render enrichment data.
    
    Args:
        repo_data: Repository data dictionary
        github_api: GitHub API client
        db_pool: Database pool (unused)
    
    Returns:
        Dictionary with Render usage detection and enrichment results
    """
    repo_full_name = repo_data.get('full_name', '')
    
    # #region agent log
    import json
    import time
    debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"render_detection.py:239","message":"detect_render_usage ENTRY","data":{"repo":repo_full_name,"already_marked_render":repo_data.get('uses_render', False)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H6"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    # If already marked as Render project (from search), verify and enrich
    if repo_data.get('uses_render'):
        logger.info(f"Repo {repo_full_name} marked as Render project, fetching render.yaml")
    
    # Try to fetch render.yaml from root
    if not repo_full_name or '/' not in repo_full_name:
        return {'uses_render': False}
    
    owner, repo = repo_full_name.split('/', 1)
    
    try:
        # Fetch render.yaml content
        render_yaml_content = await github_api.get_file_contents(owner, repo, 'render.yaml')
        
        # #region agent log
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"render_detection.py:266","message":"render.yaml fetch result","data":{"repo":repo_full_name,"found":render_yaml_content is not None,"size":len(render_yaml_content) if render_yaml_content else 0},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H6"}) + '\n')
        except Exception:
            pass
        # #endregion
        
        if not render_yaml_content:
            # No render.yaml found
            return {'uses_render': False}
        
        logger.info(f"Found render.yaml for {repo_full_name}")
        
        # Parse render.yaml
        render_config = parse_render_yaml(render_yaml_content)
        
        # Check for Dockerfile patterns (optional)
        dockerfile_content = await github_api.get_file_contents(owner, repo, 'Dockerfile')
        docker_patterns = scan_dockerfile_for_render(dockerfile_content) if dockerfile_content else {}
        
        # Calculate complexity
        complexity_score = calculate_render_complexity(render_config, docker_patterns)
        
        # Categorize project
        render_category = categorize_render_project(repo_data)
        
        # Check for deploy button (look for render button in README)
        readme = repo_data.get('readme_content', '')
        has_blueprint_button = 'render.com/deploy' in readme.lower() if readme else False
        
        # Return full enrichment data
        return {
            'uses_render': True,
            'render_category': render_category,
            'services': render_config.get('services', []),
            'databases': render_config.get('databases', []),
            'service_count': render_config.get('service_count', 0),
            'complexity_score': complexity_score,
            'has_blueprint_button': has_blueprint_button
        }
        
    except Exception as e:
        # #region agent log
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"render_detection.py:304","message":"detect_render_usage EXCEPTION","data":{"repo":repo_full_name,"error_type":type(e).__name__,"error_msg":str(e)[:300]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","hypothesisId":"H6"}) + '\n')
        except Exception:
            pass
        # #endregion
        logger.debug(f"Failed to fetch/parse render.yaml for {repo_full_name}: {e}")
        return {'uses_render': False}


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
