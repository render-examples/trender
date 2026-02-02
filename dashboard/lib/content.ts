/**
 * Content configuration for the dashboard
 * This file contains all user-facing copy to make it easily configurable
 */

export const workflowPanelContent = {
  title: 'Why Render Workflows for data engineering?',
  paragraphs: [
    `Modern data engineering demands orchestration tools that can handle complexity at scale without 
operational overhead. Render Workflows delivers this for Trender's ETL pipeline. This workflow 
coordinates parallel data extraction across multiple GitHub language ecosystems (Python, TypeScript, 
Go) and Render projects, dynamically spawning subtasks to batch-process repositories efficiently.`,
    `What makes Workflows compelling for data engineers: native parallel execution for I/O-bound 
operations, hierarchical task composition that mirrors real data pipeline patterns, built-in 
retry and error handling without custom code, and detailed execution observability for 
debugging and optimization. This approach avoids the complexity of managing Airflow, Prefect, or 
Dagster infrastructure while getting production-grade orchestration. The result: scalable data 
pipelines that run reliably with zero infrastructure management.`,
  ],
}

