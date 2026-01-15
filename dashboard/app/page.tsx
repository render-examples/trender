import Link from 'next/link'
import {
  getTopRepos,
  getLatestWorkflowStats,
  getRenderShowcase,
  getDashboardStats,
} from '@/lib/db'

export const dynamic = 'force-dynamic'

export default async function Home({
  searchParams,
}: {
  searchParams: { language?: string; render?: string }
}) {
  const selectedLanguage = searchParams.language
  const renderOnly = searchParams.render === 'true'

  // Fetch data
  const [repos, workflowStats, renderProjects, dashboardStats] = await Promise.all([
    getTopRepos(100, selectedLanguage, renderOnly),
    getLatestWorkflowStats(),
    getRenderShowcase(3),
    getDashboardStats(),
  ])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg shadow-lg p-8 mb-8 text-white">
        <h1 className="text-4xl font-bold mb-4">GitHub Trending Analytics</h1>
        <p className="text-xl mb-6">
          Discover emerging tools before they hit mainstream across Python, TypeScript/Next.js,
          and Go ecosystems
        </p>

        {/* Workflow Stats */}
        {workflowStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div className="bg-white/10 rounded p-4">
              <div className="text-3xl font-bold">
                {dashboardStats?.total_repos || 0}
              </div>
              <div className="text-sm opacity-90">Repositories Analyzed</div>
            </div>
            <div className="bg-white/10 rounded p-4">
              <div className="text-3xl font-bold">
                {workflowStats.parallel_speedup_factor?.toFixed(1)}x
              </div>
              <div className="text-sm opacity-90">Parallel Speedup</div>
            </div>
            <div className="bg-white/10 rounded p-4">
              <div className="text-3xl font-bold">
                {workflowStats.total_duration_seconds?.toFixed(1)}s
              </div>
              <div className="text-sm opacity-90">Last Run Duration</div>
            </div>
            <div className="bg-white/10 rounded p-4">
              <div className="text-3xl font-bold">
                {dashboardStats?.render_repos || 0}
              </div>
              <div className="text-sm opacity-90">Render Projects</div>
            </div>
          </div>
        )}
      </div>

      {/* Render Spotlight Banner */}
      {renderProjects.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-purple-900">
              Render Spotlight
            </h2>
            <Link
              href="/render"
              className="text-purple-600 hover:text-purple-800 font-medium"
            >
              View All →
            </Link>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            {renderProjects.slice(0, 3).map((project: any) => (
              <Link
                key={project.repo_full_name}
                href={`/repo/${project.repo_full_name}`}
                className="bg-white border border-purple-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-purple-600">
                    {project.render_category}
                  </span>
                  <span className="text-sm text-gray-500">
                    ⭐ {project.stars?.toLocaleString()}
                  </span>
                </div>
                <h3 className="font-bold text-gray-900 mb-1">
                  {project.repo_full_name}
                </h3>
                <p className="text-sm text-gray-600 line-clamp-2">
                  {project.description}
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          <div>
            <label className="text-sm font-medium text-gray-700 mr-2">
              Language:
            </label>
            <select
              className="border border-gray-300 rounded px-3 py-1"
              value={selectedLanguage || 'all'}
              onChange={(e) => {
                const lang = e.target.value === 'all' ? '' : e.target.value
                window.location.href = `/?${lang ? `language=${lang}` : ''}${renderOnly ? '&render=true' : ''}`
              }}
            >
              <option value="all">All Languages</option>
              <option value="Python">Python</option>
              <option value="TypeScript">TypeScript</option>
              <option value="Go">Go</option>
            </select>
          </div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={renderOnly}
              onChange={(e) => {
                const checked = e.target.checked
                window.location.href = `/?${selectedLanguage ? `language=${selectedLanguage}` : ''}${checked ? '&render=true' : ''}`
              }}
              className="mr-2"
            />
            <span className="text-sm font-medium text-gray-700">
              Show only Render projects
            </span>
          </label>
        </div>
      </div>

      {/* Repositories Grid */}
      <div className="grid gap-4">
        <h2 className="text-2xl font-bold text-gray-900">
          Top Trending Repositories
        </h2>
        {repos.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
            No repositories found. Trigger a workflow run to populate data.
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {repos.map((repo: any, index: number) => (
              <Link
                key={repo.repo_full_name}
                href={`/repo/${repo.repo_full_name}`}
                className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6 border border-gray-200"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-gray-400">
                      #{repo.rank_overall || index + 1}
                    </span>
                    {repo.uses_render && (
                      <span className="bg-purple-100 text-purple-800 text-xs font-medium px-2 py-1 rounded">
                        Render
                      </span>
                    )}
                  </div>
                  <span className="text-sm text-gray-500">{repo.language}</span>
                </div>

                <h3 className="text-lg font-bold text-gray-900 mb-2">
                  {repo.repo_full_name}
                </h3>
                <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                  {repo.description || 'No description available'}
                </p>

                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-gray-500">Stars</div>
                    <div className="font-semibold">
                      {repo.stars?.toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Momentum</div>
                    <div className="font-semibold">
                      {repo.momentum_score?.toFixed(1)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Velocity</div>
                    <div className="font-semibold">
                      {repo.star_velocity?.toFixed(1)}%
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Last Updated */}
      {dashboardStats?.last_updated && (
        <div className="mt-8 text-center text-sm text-gray-500">
          Last updated:{' '}
          {new Date(dashboardStats.last_updated).toLocaleString()}
        </div>
      )}
    </div>
  )
}
