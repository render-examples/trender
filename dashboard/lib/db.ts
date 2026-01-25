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
 * Matches the analytics_trending_repos_current view
 */
export interface Repository {
  repo_full_name: string;
  repo_url: string;
  language: string;
  stars: number;
  star_velocity: number;
  activity_score: number;
  momentum_score: number;
  description: string;
  readme_content: string | null;
  render_category: string | null;
  rank_overall: number;
  rank_in_language: number;
  snapshot_date: Date;
  last_updated: Date;
}

/**
 * Workflow execution stats type
 */
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
    AND repo_full_name !~ '^vercel'
  `;

  const params: any[] = [];
  let paramIndex = 1;

  if (language) {
    queryText += ` AND language = $${paramIndex}`;
    params.push(language);
    paramIndex++;
  }

  if (renderOnly) {
    queryText += ` AND language = 'render'`;
  }

  queryText += ` ORDER BY stars DESC LIMIT $${paramIndex}`;
  params.push(limit);

  const result = await query<Repository>(queryText, params);
  return result.rows;
}

/**
 * Get repository details by full name
 */
export async function getRepoDetails(fullName: string): Promise<Repository | null> {
  const result = await query<Repository>(
    `SELECT * FROM analytics_trending_repos_current 
     WHERE repo_full_name = $1 
     AND repo_full_name !~ '^vercel'`,
    [fullName]
  );
  return result.rows[0] || null;
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
     AND repo_full_name !~ '^vercel'
     ORDER BY stars DESC
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
