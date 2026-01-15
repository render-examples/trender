"""
Metrics Calculation Module
Calculates momentum, activity, and velocity scores for repositories.
"""

from typing import Dict, List
from datetime import datetime


def calculate_metrics(enriched_repos: List[Dict]) -> List[Dict]:
    """
    Calculate momentum and activity scores for repositories.

    Args:
        enriched_repos: List of repository dictionaries with enriched data

    Returns:
        List of repositories with calculated metrics
    """
    for repo in enriched_repos:
        # Star velocity calculation
        # (recent star growth / total stars) * 100
        stars = repo.get('stars', 0)
        stars_last_7_days = repo.get('stars_last_7_days', 0)

        if stars > 0:
            repo['star_velocity'] = round((stars_last_7_days / stars) * 100, 2)
        else:
            repo['star_velocity'] = 0.0

        # Activity score (weighted formula)
        # Combines commits, issues closed, and active contributors
        commits = repo.get('commits_last_7_days', 0)
        issues_closed = repo.get('issues_closed_last_7_days', 0)
        contributors = repo.get('active_contributors', 0)

        repo['activity_score'] = round(
            commits * 0.4 +
            issues_closed * 0.3 +
            contributors * 0.3,
            2
        )

        # Momentum score
        # Combines star velocity and activity
        repo['momentum_score'] = round(
            repo['star_velocity'] * 0.4 +
            repo['activity_score'] * 0.6,
            2
        )

        # Apply Render boost multiplier for marketing visibility
        if repo.get('uses_render'):
            repo['momentum_score'] = round(repo['momentum_score'] * 1.2, 2)

        # Freshness penalty for old repos
        created_at = repo.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = None

            if created_at:
                age_days = (datetime.utcnow() - created_at.replace(tzinfo=None)).days
                if age_days > 180:
                    repo['momentum_score'] = round(repo['momentum_score'] * 0.9, 2)

    return enriched_repos


def calculate_star_velocity(current_stars: int, stars_gained: int) -> float:
    """
    Calculate star velocity metric.

    Args:
        current_stars: Current total stars
        stars_gained: Stars gained in recent period

    Returns:
        Star velocity percentage
    """
    if current_stars == 0:
        return 0.0

    return round((stars_gained / current_stars) * 100, 2)


def calculate_activity_score(commits: int, issues_closed: int,
                             contributors: int) -> float:
    """
    Calculate activity score based on repository metrics.

    Args:
        commits: Number of commits in period
        issues_closed: Number of issues closed in period
        contributors: Number of active contributors

    Returns:
        Activity score
    """
    return round(
        commits * 0.4 +
        issues_closed * 0.3 +
        contributors * 0.3,
        2
    )


def calculate_momentum_score(star_velocity: float, activity_score: float,
                             uses_render: bool = False,
                             repo_age_days: int = 0) -> float:
    """
    Calculate momentum score combining velocity and activity.

    Args:
        star_velocity: Star velocity percentage
        activity_score: Activity score
        uses_render: Whether the repo uses Render
        repo_age_days: Age of repository in days

    Returns:
        Momentum score
    """
    momentum = star_velocity * 0.4 + activity_score * 0.6

    # Apply Render boost
    if uses_render:
        momentum *= 1.2

    # Apply freshness penalty
    if repo_age_days > 180:
        momentum *= 0.9

    return round(momentum, 2)
