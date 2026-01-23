/**
 * PostgreSQL Database Connection Module for Trender Dashboard
 */

import { Pool, QueryResult, QueryResultRow } from 'pg';

// Database connection pool
let pool: Pool | null = null;

/**
 * Get or create database connection pool
 */
export function getPool(): Pool {
  if (!pool) {
    const connectionString = process.env.DATABASE_URL;

    if (!connectionString) {
      throw new Error('DATABASE_URL environment variable is not set');
    }

    pool = new Pool({
      connectionString,
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
      ssl: {
        rejectUnauthorized: false,
      },
    });

    pool.on('error', (err) => {
      console.error('Unexpected database error:', err);
    });
  }

  return pool;
}

/**
 * Execute a database query
 */
export async function query<T extends QueryResultRow = any>(
  text: string,
  params?: any[]
): Promise<QueryResult<T>> {
  const pool = getPool();
  return pool.query<T>(text, params);
}

/**
 * Repository type definition
 */
export interface Repository {
  id: number;
  repo_full_name: string;
  repo_url: string;
  language: string;
  stars: number;
  star_velocity: number;
  activity_score: number;
  momentum_score: number;
  commits_last_7_days: number;
  issues_closed_last_7_days: number;
  active_contributors: number;
  description: string;
  readme_content: string | null;
  uses_render: boolean;
  render_category: string | null;
  render_services: string[];
  has_blueprint_button: boolean;
  render_complexity_score: number;
  created_at: Date;
  last_updated: Date;
}

/**
 * Workflow execution stats type
 */
export interface WorkflowStats {
  id: number;
  execution_id: string;
  started_at: Date;
  completed_at: Date;
  duration_seconds: number;
  total_tasks_executed: number;
  successful_tasks: number;
  failed_tasks: number;
  retried_tasks: number;
  repos_analyzed: number;
  languages_processed: number;
  parallel_speedup_factor: number;
  avg_task_spinup_ms: number;
  max_concurrent_tasks: number;
  status: string;
}

/**
 * Get top trending repositories
 */
export async function getTopRepos(
  limit: number = 100,
  language?: string,
  renderOnly: boolean = false
): Promise<Repository[]> {
  let queryText = `
    SELECT * FROM analytics_trending_repos_current
    WHERE 1=1
  `;

  const params: any[] = [];
  let paramIndex = 1;

  if (language) {
    queryText += ` AND language = $${paramIndex}`;
    params.push(language);
    paramIndex++;
  }

  if (renderOnly) {
    queryText += ` AND uses_render = true`;
  }

  queryText += ` ORDER BY momentum_score DESC LIMIT $${paramIndex}`;
  params.push(limit);

  const result = await query<Repository>(queryText, params);
  return result.rows;
}

/**
 * Get Render showcase projects
 */
export async function getRenderShowcase(limit: number = 50): Promise<any[]> {
  const result = await query(
    `SELECT * FROM analytics_render_showcase
     ORDER BY momentum_score DESC
     LIMIT $1`,
    [limit]
  );
  return result.rows;
}

/**
 * Get language statistics
 */
export async function getLanguageStats(): Promise<any[]> {
  const result = await query(`
    SELECT * FROM analytics_language_trends
    ORDER BY total_repos DESC
  `);
  return result.rows;
}

/**
 * Get latest workflow execution stats
 */
export async function getLatestWorkflowStats(): Promise<WorkflowStats | null> {
  const result = await query<WorkflowStats>(
    `SELECT * FROM analytics_workflow_performance
     ORDER BY execution_date DESC
     LIMIT 1`
  );
  return result.rows[0] || null;
}

/**
 * Get repository details by full name
 */
export async function getRepoDetails(fullName: string): Promise<Repository | null> {
  const result = await query<Repository>(
    `SELECT * FROM analytics_trending_repos_current WHERE repo_full_name = $1`,
    [fullName]
  );
  return result.rows[0] || null;
}

/**
 * Get repository snapshots (historical data)
 */
export async function getRepoSnapshots(fullName: string, limit: number = 30): Promise<any[]> {
  const result = await query(
    `SELECT * FROM analytics_repo_history
     WHERE repo_full_name = $1
     ORDER BY snapshot_date DESC
     LIMIT $2`,
    [fullName, limit]
  );
  return result.rows;
}

/**
 * Get workflow execution history
 */
export async function getWorkflowHistory(limit: number = 10): Promise<WorkflowStats[]> {
  const result = await query<WorkflowStats>(
    `SELECT * FROM analytics_workflow_performance
     ORDER BY execution_date DESC
     LIMIT $1`,
    [limit]
  );
  return result.rows;
}

/**
 * Get language-specific top repos
 */
export async function getLanguageTopRepos(
  language: string,
  limit: number = 50
): Promise<Repository[]> {
  const result = await query<Repository>(
    `SELECT * FROM analytics_language_rankings
     WHERE language_name = $1
     ORDER BY rank_in_language
     LIMIT $2`,
    [language, limit]
  );
  return result.rows;
}

/**
 * Get ecosystem statistics
 */
export async function getEcosystemStats(): Promise<{
  total_projects: number;
  total_stars: number;
  by_category: any[];
}> {
  const totalResult = await query(
    `SELECT COUNT(*) as total_projects, SUM(stars) as total_stars
     FROM analytics_render_showcase`
  );

  const categoryResult = await query(
    `SELECT render_category, COUNT(*) as count, SUM(stars) as total_stars
     FROM analytics_render_showcase
     GROUP BY render_category
     ORDER BY total_stars DESC`
  );

  return {
    total_projects: parseInt(totalResult.rows[0]?.total_projects || '0'),
    total_stars: parseInt(totalResult.rows[0]?.total_stars || '0'),
    by_category: categoryResult.rows,
  };
}

/**
 * Get dashboard statistics
 */
export async function getDashboardStats(): Promise<{
  total_repos: number;
  render_repos: number;
  last_updated: Date | null;
}> {
  const totalReposResult = await query(
    `SELECT COUNT(*) as total_repos, MAX(last_updated) as last_updated
     FROM analytics_trending_repos_current`
  );

  const renderReposResult = await query(
    `SELECT COUNT(*) as render_repos
     FROM analytics_trending_repos_current
     WHERE uses_render = true`
  );

  return {
    total_repos: parseInt(totalReposResult.rows[0]?.total_repos || '0'),
    render_repos: parseInt(renderReposResult.rows[0]?.render_repos || '0'),
    last_updated: totalReposResult.rows[0]?.last_updated || null,
  };
}

/**
 * Get top repositories by language
 */
export async function getTopReposByLanguage(
  language: string,
  limit: number = 50
): Promise<Repository[]> {
  const result = await query<Repository>(
    `SELECT * FROM analytics_trending_repos_current
     WHERE language = $1
     ORDER BY momentum_score DESC
     LIMIT $2`,
    [language, limit]
  );
  return result.rows;
}

/**
 * Close database connection pool
 */
export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}
