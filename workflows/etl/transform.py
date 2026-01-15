"""
Transform Module
Transforms and ranks repository data for analytics layer.
"""

from typing import List, Dict
from datetime import datetime


def transform_and_rank(repos: List[Dict], overall_limit: int = 100,
                      per_language_limit: int = 50) -> List[Dict]:
    """
    Transform repository data and calculate rankings.

    Args:
        repos: List of repository dictionaries with calculated metrics
        overall_limit: Number of top repos to include in overall ranking
        per_language_limit: Number of top repos per language

    Returns:
        List of transformed and ranked repository dictionaries
    """
    if not repos:
        return []

    # Sort by momentum score for overall ranking
    repos_sorted = sorted(repos, key=lambda x: x.get('momentum_score', 0), reverse=True)

    # Assign overall ranks
    for idx, repo in enumerate(repos_sorted[:overall_limit]):
        repo['rank_overall'] = idx + 1

    # Group by language for per-language ranking
    language_groups = {}
    for repo in repos:
        lang = repo.get('language', 'Unknown')
        if lang not in language_groups:
            language_groups[lang] = []
        language_groups[lang].append(repo)

    # Assign per-language ranks
    for lang, lang_repos in language_groups.items():
        lang_sorted = sorted(lang_repos, key=lambda x: x.get('momentum_score', 0), reverse=True)
        for idx, repo in enumerate(lang_sorted[:per_language_limit]):
            repo['rank_in_language'] = idx + 1

    # Filter to only include ranked repos
    ranked_repos = [
        repo for repo in repos
        if repo.get('rank_overall') or repo.get('rank_in_language')
    ]

    return ranked_repos


def deduplicate_repos(repo_lists: List) -> List[Dict]:
    """
    Deduplicate repositories across multiple result sets.

    Args:
        repo_lists: List of repository lists or a single list

    Returns:
        Deduplicated list of repository dictionaries
    """
    seen = set()
    unique_repos = []

    # Flatten if needed
    if repo_lists and isinstance(repo_lists[0], list):
        all_repos = []
        for repo_list in repo_lists:
            if isinstance(repo_list, list):
                all_repos.extend(repo_list)
            else:
                all_repos.append(repo_list)
    else:
        all_repos = repo_lists

    for repo in all_repos:
        if isinstance(repo, dict):
            repo_name = repo.get('repo_full_name') or repo.get('full_name')
            if repo_name and repo_name not in seen:
                seen.add(repo_name)
                unique_repos.append(repo)

    return unique_repos


def chunk_list(items: List, size: int = 10) -> List[List]:
    """
    Split a list into chunks of specified size.

    Args:
        items: List to chunk
        size: Chunk size

    Returns:
        List of chunked lists
    """
    return [items[i:i + size] for i in range(0, len(items), size)]
