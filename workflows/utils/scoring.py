"""
Scoring algorithms for repository ranking and momentum calculation.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def calculate_recency_score(created_at, now: datetime) -> float:
    """
    Calculate recency score based on repo age with exponential decay.
    Heavily favors newer repos to prioritize emerging projects.

    Args:
        created_at: Repository creation datetime (string or datetime object)
        now: Current datetime for calculating age

    Returns:
        Recency score between 0.01 and 1.0
    """
    if not created_at:
        return 0.0

    # Ensure created_at is timezone-aware
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    elif created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    age_days = (now - created_at).days

    # Exponential decay: heavily favor very recent repos
    if age_days <= 14:
        return 1.0
    elif age_days <= 30:
        return 0.85
    elif age_days <= 60:
        return 0.60
    elif age_days <= 90:
        return 0.35
    elif age_days <= 180:
        return 0.15
    elif age_days <= 365:
        return 0.05
    else:
        return 0.01  # Minimal score for older repos


def calculate_momentum_score(
    stars: int,
    created_at,
    now: datetime,
    max_stars: int,
    recency_weight: float = 0.7,
    stars_weight: float = 0.3
) -> float:
    """
    Calculate momentum score using star-recency formula.

    Formula: (recency_score * recency_weight) + (normalized_stars * stars_weight)

    This heavily favors newer repos to surface emerging projects.

    Args:
        stars: Number of GitHub stars
        created_at: Repository creation datetime
        now: Current datetime for calculating age
        max_stars: Maximum stars for normalization (per category)
        recency_weight: Weight for recency component (default 0.7)
        stars_weight: Weight for stars component (default 0.3)

    Returns:
        Momentum score between 0.0 and 1.0
    """
    # Normalize stars based on max (general vs render)
    normalized_stars = stars / max_stars if max_stars > 0 else 0.0

    # Calculate recency score
    recency_score = calculate_recency_score(created_at, now)

    # Final momentum score: weighted combination
    momentum_score = (recency_score * recency_weight) + (normalized_stars * stars_weight)

    return momentum_score

