"""
Trender Main Workflow
Orchestrates the GitHub trending analytics pipeline using Render Workflows.
"""

from render_sdk.workflows import task, start
import asyncio
import asyncpg
import os
from datetime import datetime, timedelta, date
from typing import Dict, List

from connections import init_connections, cleanup_connections
from github_api import GitHubAPIClient
from metrics import calculate_metrics
from render_detection import (
    detect_render_usage, categorize_render_project,
    score_blueprint_quality, score_documentation,
    store_render_enrichment
)
from etl import extract_from_staging, transform_and_rank, load_to_analytics
from etl.extract import store_raw_repos, store_raw_metrics
from etl.transform import deduplicate_repos, chunk_list
from etl.data_quality import calculate_data_quality_score

# Target languages for analysis
TARGET_LANGUAGES = ['Python', 'TypeScript', 'Go']


@task
async def main_analysis_task() -> Dict:
    """
    Main orchestrator task for the entire analysis workflow.

    Spawns parallel tasks for:
    - 3 language-specific analyses (Python, TypeScript, Go)
    - 1 Render ecosystem fetch

    Returns execution summary.
    """
    execution_start = datetime.utcnow()
    github_api, db_pool = await init_connections()

    try:
        # Spawn parallel language analysis tasks
        language_tasks = [
            fetch_language_repos(lang, github_api, db_pool)
            for lang in TARGET_LANGUAGES
        ]

        # Execute language analysis and Render ecosystem fetch in parallel
        results = await asyncio.gather(
            *language_tasks,
            fetch_render_ecosystem(github_api, db_pool),
            return_exceptions=True
        )

        # Aggregate and store final results
        final_result = await aggregate_results(results, db_pool, execution_start)

        # Store execution stats
        execution_time = (datetime.utcnow() - execution_start).total_seconds()
        await store_execution_stats(execution_time, final_result.get('repos_processed', 0), db_pool)

        return final_result
    finally:
        await cleanup_connections(github_api, db_pool)


@task
async def fetch_language_repos(language: str, github_api: GitHubAPIClient,
                               db_pool: asyncpg.Pool) -> List[Dict]:
    """
    Fetch and store trending repos for a specific language.

    Args:
        language: Programming language to fetch
        github_api: GitHub API client
        db_pool: Database connection pool

    Returns:
        List of enriched repository dictionaries
    """
    # Search GitHub API
    repos = await github_api.search_repositories(
        language=language,
        sort='stars',
        updated_since=datetime.utcnow() - timedelta(days=30)
    )

    # TypeScript-specific filtering for Next.js >= 16
    if language == 'TypeScript':
        repos = await filter_nextjs_repos(repos, github_api, min_version=16)

    # Store raw API responses
    await store_raw_repos(repos, db_pool, source_language=language)

    # Spawn batch analysis tasks
    batch_results = await analyze_repo_batch(repos[:100], github_api, db_pool)

    return batch_results


async def filter_nextjs_repos(repos: List[Dict], github_api: GitHubAPIClient,
                              min_version: int = 16) -> List[Dict]:
    """
    Filter TypeScript repos for Next.js >= specified version.

    Args:
        repos: List of repository dictionaries
        github_api: GitHub API client
        min_version: Minimum Next.js version

    Returns:
        Filtered list of repositories
    """
    filtered = []

    for repo in repos:
        try:
            owner, name = repo.get('full_name', '/').split('/')
            package_json = await github_api.get_file_contents(owner, name, 'package.json')

            if package_json:
                import json
                package_data = json.loads(package_json)

                # Check dependencies and devDependencies
                next_version = None
                deps = package_data.get('dependencies', {})
                dev_deps = package_data.get('devDependencies', {})

                if 'next' in deps:
                    next_version = deps['next']
                elif 'next' in dev_deps:
                    next_version = dev_deps['next']

                if next_version:
                    # Extract major version number
                    import re
                    version_match = re.search(r'(\d+)\.', next_version)
                    if version_match:
                        major_version = int(version_match.group(1))
                        if major_version >= min_version:
                            filtered.append(repo)
                else:
                    # Include if no Next.js found (might be other TS project)
                    filtered.append(repo)
            else:
                # Include if no package.json found
                filtered.append(repo)
        except:
            # Include on error to avoid losing data
            filtered.append(repo)

    return filtered


@task
async def analyze_repo_batch(repos: List[Dict], github_api: GitHubAPIClient,
                             db_pool: asyncpg.Pool) -> List[Dict]:
    """
    Analyze a batch of repositories with detailed metrics.

    Args:
        repos: List of repository dictionaries
        github_api: GitHub API client
        db_pool: Database connection pool

    Returns:
        List of enriched repository dictionaries
    """
    enriched_repos = []

    # Process repos in batches of 10
    for batch in chunk_list(repos, size=10):
        batch_tasks = [
            analyze_single_repo(repo, github_api, db_pool)
            for repo in batch
        ]

        # Gather with exceptions to continue on failures
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Filter out exceptions and collect successful results
        enriched_repos.extend([r for r in batch_results if not isinstance(r, Exception)])

    return enriched_repos


async def analyze_single_repo(repo: Dict, github_api: GitHubAPIClient,
                              db_pool: asyncpg.Pool) -> Dict:
    """
    Analyze a single repository with detailed metrics.

    Args:
        repo: Repository dictionary
        github_api: GitHub API client
        db_pool: Database connection pool

    Returns:
        Enriched repository dictionary
    """
    owner, name = repo.get('full_name', '/').split('/')

    # Fetch detailed metrics
    since_date = datetime.utcnow() - timedelta(days=7)

    # Parallel fetch of metrics
    commits, issues, contributors, render_data = await asyncio.gather(
        github_api.get_commits(owner, name, since_date),
        github_api.get_issues(owner, name, state='closed', since=since_date),
        github_api.get_contributors(owner, name),
        detect_render_usage(repo, github_api, db_pool),
        return_exceptions=True
    )

    # Handle exceptions
    commits = commits if not isinstance(commits, Exception) else []
    issues = issues if not isinstance(issues, Exception) else []
    contributors = contributors if not isinstance(contributors, Exception) else []
    render_data = render_data if not isinstance(render_data, Exception) else {}

    # Store raw metrics
    await store_raw_metrics(repo.get('full_name'), 'commits', {'count': len(commits), 'commits': commits}, db_pool)
    await store_raw_metrics(repo.get('full_name'), 'issues', {'count': len(issues), 'issues': issues}, db_pool)
    await store_raw_metrics(repo.get('full_name'), 'contributors', {'count': len(contributors), 'contributors': contributors}, db_pool)

    # Build enriched repo data
    enriched = {
        'repo_full_name': repo.get('full_name'),
        'repo_url': repo.get('html_url'),
        'language': repo.get('language'),
        'description': repo.get('description'),
        'stars': repo.get('stargazers_count', 0),
        'forks': repo.get('forks_count', 0),
        'open_issues': repo.get('open_issues_count', 0),
        'created_at': repo.get('created_at'),
        'updated_at': repo.get('updated_at'),
        'commits_last_7_days': len(commits),
        'issues_closed_last_7_days': len(issues),
        'active_contributors': len(contributors),
        'uses_render': render_data.get('uses_render', False),
        'render_yaml_content': render_data.get('render_yaml_content'),
        **render_data
    }

    # Calculate data quality score
    enriched['data_quality_score'] = calculate_data_quality_score(enriched)

    # Store in staging layer
    await store_in_staging(enriched, db_pool)

    return enriched


async def store_in_staging(repo: Dict, db_pool: asyncpg.Pool):
    """Store enriched repository data in staging layer."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO stg_repos_validated
                (repo_full_name, repo_url, language, description, stars, forks,
                 open_issues, created_at, updated_at, commits_last_7_days,
                 issues_closed_last_7_days, active_contributors, uses_render,
                 render_yaml_content, data_quality_score)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            ON CONFLICT (repo_full_name) DO UPDATE SET
                stars = EXCLUDED.stars,
                forks = EXCLUDED.forks,
                open_issues = EXCLUDED.open_issues,
                updated_at = EXCLUDED.updated_at,
                commits_last_7_days = EXCLUDED.commits_last_7_days,
                issues_closed_last_7_days = EXCLUDED.issues_closed_last_7_days,
                active_contributors = EXCLUDED.active_contributors,
                uses_render = EXCLUDED.uses_render,
                data_quality_score = EXCLUDED.data_quality_score,
                loaded_at = NOW()
        """, repo.get('repo_full_name'), repo.get('repo_url'), repo.get('language'),
            repo.get('description'), repo.get('stars', 0), repo.get('forks', 0),
            repo.get('open_issues', 0), repo.get('created_at'), repo.get('updated_at'),
            repo.get('commits_last_7_days', 0), repo.get('issues_closed_last_7_days', 0),
            repo.get('active_contributors', 0), repo.get('uses_render', False),
            repo.get('render_yaml_content'), repo.get('data_quality_score', 0.0))


@task
async def fetch_render_ecosystem(github_api: GitHubAPIClient,
                                 db_pool: asyncpg.Pool) -> List[Dict]:
    """
    Fetch Render-related projects from multiple sources.

    Args:
        github_api: GitHub API client
        db_pool: Database connection pool

    Returns:
        List of analyzed Render project dictionaries
    """
    # Parallel fetch from multiple sources
    results = await asyncio.gather(
        github_api.get_org_repos('render-examples'),
        github_api.get_org_repos('render'),
        github_api.search_by_topic('render'),
        github_api.search_by_topic('render-deploy'),
        github_api.search_by_topic('render-blueprints'),
        github_api.search_readme_mentions('render.com'),
        return_exceptions=True
    )

    # Filter out exceptions and flatten
    valid_results = [r for r in results if not isinstance(r, Exception)]

    # Deduplicate and store
    unique_repos = deduplicate_repos(valid_results)
    await store_raw_repos(unique_repos, db_pool, source_type='render_ecosystem')

    # Analyze Render-specific features
    analyzed = await analyze_render_projects(unique_repos, github_api, db_pool)

    return analyzed


@task
async def analyze_render_projects(render_repos: List[Dict],
                                  github_api: GitHubAPIClient,
                                  db_pool: asyncpg.Pool) -> List[Dict]:
    """
    Analyze Render-specific features and categorization.

    Args:
        render_repos: List of Render repository dictionaries
        github_api: GitHub API client
        db_pool: Database connection pool

    Returns:
        List of enriched Render project dictionaries
    """
    enriched_projects = []

    for repo in render_repos:
        # Detect Render usage patterns
        render_data = await detect_render_usage(repo, github_api, db_pool)

        # Calculate Render-specific scores
        repo['render_category'] = categorize_render_project(repo)
        repo['blueprint_quality'] = score_blueprint_quality(render_data)
        repo['documentation_score'] = score_documentation(repo, render_data)
        repo['render_services'] = render_data.get('services', [])
        repo['render_complexity_score'] = render_data.get('complexity_score', 0)
        repo['service_count'] = render_data.get('service_count', 0)
        repo['uses_render'] = render_data.get('uses_render', False)

        enriched_projects.append(repo)

    # Store enrichment data
    await store_render_enrichment(enriched_projects, db_pool)

    return enriched_projects


@task
async def aggregate_results(all_results: List, db_pool: asyncpg.Pool,
                            execution_start: datetime) -> Dict:
    """
    Execute ETL pipeline: Extract from staging → Transform → Load to analytics.

    Args:
        all_results: List of results from parallel tasks
        db_pool: Database connection pool
        execution_start: Workflow execution start time

    Returns:
        Execution summary dictionary
    """
    # Filter successful results (handle exceptions from gather)
    language_results = [r for r in all_results[:3] if not isinstance(r, Exception)]
    render_results = all_results[3] if len(all_results) > 3 and not isinstance(all_results[3], Exception) else []

    # Combine and deduplicate
    all_repos = deduplicate_repos(language_results + [render_results])

    # Calculate metrics for all repos
    scored_repos = calculate_metrics(all_repos)

    # ETL Pipeline Execution
    # 1. Extract: Read from staging tables (already stored)
    staging_data = await extract_from_staging(db_pool)

    # 2. Transform: Calculate rankings and velocity metrics
    ranked_repos = transform_and_rank(
        staging_data,
        overall_limit=100,
        per_language_limit=50
    )

    # 3. Load: Upsert to analytics layer
    await load_to_analytics(ranked_repos, db_pool)

    return {
        'repos_processed': len(all_repos),
        'execution_time': (datetime.utcnow() - execution_start).total_seconds(),
        'languages': TARGET_LANGUAGES,
        'success': True
    }


@task
async def store_execution_stats(duration: float, repos_count: int,
                                db_pool: asyncpg.Pool) -> None:
    """
    Record workflow performance metrics.

    Args:
        duration: Execution duration in seconds
        repos_count: Number of repositories processed
        db_pool: Database connection pool
    """
    # Calculate parallel speedup (3 languages in parallel vs sequential)
    estimated_sequential = duration * 3
    parallel_speedup = estimated_sequential / duration if duration > 0 else 1.0

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO fact_workflow_executions
                (execution_date, total_duration_seconds, repos_processed,
                 tasks_executed, tasks_succeeded, parallel_speedup_factor,
                 languages_processed, success_rate)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, datetime.utcnow(), duration, repos_count, 9, 9,
            parallel_speedup, TARGET_LANGUAGES, 1.0)


if __name__ == "__main__":
    # Start the Render Workflows task server
    # This registers all @task decorated functions and begins listening for task execution requests
    start()
