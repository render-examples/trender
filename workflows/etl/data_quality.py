"""
Data Quality Module
Calculates data quality scores for repositories in staging layer.
"""

from typing import Dict
from datetime import datetime, timedelta


def calculate_data_quality_score(repo: Dict) -> float:
    """
    Calculate data quality score for a repository.

    The score is based on:
    - Completeness: Presence of key fields (40%)
    - Freshness: How recently the repo was updated (30%)
    - Validity: Data consistency and ranges (30%)

    Args:
        repo: Repository data dictionary

    Returns:
        Data quality score between 0.0 and 1.0
    """
    scores = []

    # Completeness Score (40%)
    completeness = calculate_completeness_score(repo)
    scores.append(completeness * 0.4)

    # Freshness Score (30%)
    freshness = calculate_freshness_score(repo)
    scores.append(freshness * 0.3)

    # Validity Score (30%)
    validity = calculate_validity_score(repo)
    scores.append(validity * 0.3)

    # Total score
    total_score = sum(scores)
    return round(total_score, 2)


def calculate_completeness_score(repo: Dict) -> float:
    """
    Calculate completeness score based on presence of key fields.

    Args:
        repo: Repository data dictionary

    Returns:
        Completeness score between 0.0 and 1.0
    """
    required_fields = [
        'repo_full_name', 'repo_url', 'language', 'stars',
        'created_at', 'updated_at'
    ]

    optional_fields = [
        'description', 'forks', 'open_issues',
        'commits_last_7_days', 'active_contributors'
    ]

    # Check required fields (70% weight)
    required_present = sum(1 for field in required_fields if repo.get(field))
    required_score = required_present / len(required_fields) * 0.7

    # Check optional fields (30% weight)
    optional_present = sum(1 for field in optional_fields if repo.get(field))
    optional_score = optional_present / len(optional_fields) * 0.3

    return required_score + optional_score


def calculate_freshness_score(repo: Dict) -> float:
    """
    Calculate freshness score based on how recently the repo was updated.

    Args:
        repo: Repository data dictionary

    Returns:
        Freshness score between 0.0 and 1.0
    """
    updated_at = repo.get('updated_at')
    if not updated_at:
        return 0.5  # Default score if no update timestamp

    # Convert to datetime if needed
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        except:
            return 0.5

    now = datetime.utcnow()
    if updated_at.tzinfo:
        import pytz
        now = now.replace(tzinfo=pytz.UTC)

    days_since_update = (now - updated_at).days

    # Scoring logic:
    # - Updated today: 1.0
    # - Updated within 7 days: 0.9
    # - Updated within 30 days: 0.7
    # - Updated within 90 days: 0.5
    # - Updated over 90 days ago: 0.3
    if days_since_update <= 1:
        return 1.0
    elif days_since_update <= 7:
        return 0.9
    elif days_since_update <= 30:
        return 0.7
    elif days_since_update <= 90:
        return 0.5
    else:
        return 0.3


def calculate_validity_score(repo: Dict) -> float:
    """
    Calculate validity score based on data consistency and ranges.

    Args:
        repo: Repository data dictionary

    Returns:
        Validity score between 0.0 and 1.0
    """
    score = 1.0

    # Check stars is non-negative
    stars = repo.get('stars', 0)
    if stars < 0:
        score -= 0.3

    # Check forks is non-negative and less than stars
    forks = repo.get('forks', 0)
    if forks < 0:
        score -= 0.2
    elif stars > 0 and forks > stars * 2:
        # Suspicious: more than 2x forks as stars
        score -= 0.1

    # Check created_at is before updated_at
    created_at = repo.get('created_at')
    updated_at = repo.get('updated_at')
    if created_at and updated_at:
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = None
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except:
                updated_at = None

        if created_at and updated_at and created_at > updated_at:
            score -= 0.2

    # Check language is valid
    valid_languages = ['Python', 'TypeScript', 'JavaScript', 'Go', 'Java',
                      'C++', 'C', 'Ruby', 'PHP', 'C#', 'Rust', 'Swift']
    language = repo.get('language')
    if not language or language not in valid_languages:
        score -= 0.1

    return max(0.0, score)
