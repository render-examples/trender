"""
ETL Module
Extract, Transform, Load pipeline for the 3-layer data architecture.
"""

from etl.extract import extract_from_staging, store_raw_repos
from etl.cleanup import cleanup_old_data, store_in_staging
from etl.load import load_to_analytics_simple
from etl.aggregate import aggregate_results

__all__ = [
    # Extract
    'extract_from_staging',
    'store_raw_repos',
    # Cleanup
    'cleanup_old_data',
    'store_in_staging',
    # Load
    'load_to_analytics_simple',
    # Aggregate
    'aggregate_results',
]
