"""
Trender Main Workflow
Orchestrates the GitHub trending analytics pipeline using Render Workflows.

This is the entry point that registers all workflow tasks and starts the task server.
"""

# CRITICAL: Add workflows directory to Python path FIRST, before any local imports
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Render SDK
from app import app

# Import all @app.task decorated functions to register them with the Workflows app
# These imports are required even though they appear unused - they register the tasks
from tasks.main_task import main_analysis_task
from tasks.language_tasks import fetch_language_repos, fetch_render_repos
from tasks.batch_analysis import analyze_repo_batch

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Development mode configuration
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'
DEV_REPO_LIMIT = int(os.getenv('DEV_REPO_LIMIT', '50'))

# Target languages for analysis
TARGET_LANGUAGES = ['Python', 'TypeScript', 'Go']


if __name__ == "__main__":
    # Start the Render Workflows task server
    # This registers all @app.task decorated functions and begins listening for task execution requests
    logger.info("Starting Render Workflows task server...")
    logger.info(f"Registered tasks: main_analysis_task, fetch_language_repos, fetch_render_repos, analyze_repo_batch")
    logger.info(f"DEV_MODE: {DEV_MODE}, Target languages: {TARGET_LANGUAGES}")
    app.start()
