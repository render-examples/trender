"""
ETL Module
Extract, Transform, Load pipeline for the 3-layer data architecture.
"""

# Use relative import since we're inside the etl package
from .extract import extract_from_staging, store_raw_repos, store_raw_metrics
from .cleanup import cleanup_old_data, store_in_staging
from .load import load_to_analytics_simple
from .aggregate import aggregate_results

__all__ = [
    # Extract
    'extract_from_staging',
    'store_raw_repos',
    'store_raw_metrics',
    # Cleanup
    'cleanup_old_data',
    'store_in_staging',
    # Load
    'load_to_analytics_simple',
    # Aggregate
    'aggregate_results',
]
