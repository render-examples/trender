import Link from 'next/link'
import { getRepoDetails, getRepoSnapshots } from '@/lib/db'

export const dynamic = 'force-dynamic'

export default async function RepoDetailPage({
  params,
}: {
  params: { owner: string; name: string }
}) {
  const repoFullName = `${params.owner}/${params.name}`
  const [repo, snapshots] = await Promise.all([
    getRepoDetails(repoFullName),
    getRepoSnapshots(repoFullName, 30),
  ])

  if (!repo) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h1 className="text-2xl font-bold text-red-900 mb-2">
            Repository Not Found
          </h1>
          <p className="text-red-700 mb-4">
            The repository "{repoFullName}" was not found in our database.
          </p>
          <Link href="/" className="text-blue-600 hover:underline">
            Back to Home
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
          <Link href="/" className="hover:text-blue-600">
            Home
          </Link>
          <span>/</span>
          <Link
            href={`/language/${repo.language}`}
            className="hover:text-blue-600"
          >
            {repo.language}
          </Link>
          <span>/</span>
          <span className="text-gray-900">{repoFullName}</span>
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          {repoFullName}
        </h1>
        <p className="text-lg text-gray-600">{repo.description}</p>
      </div>

      {/* Overview Card */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div>
            <div className="text-sm text-gray-500 mb-1">Stars</div>
            <div className="text-3xl font-bold text-gray-900">
              ⭐ {repo.stars?.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Forks</div>
            <div className="text-3xl font-bold text-gray-900">
              🔀 {repo.forks?.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Momentum Score</div>
            <div className="text-3xl font-bold text-green-600">
              {repo.momentum_score?.toFixed(1)}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Overall Rank</div>
            <div className="text-3xl font-bold text-blue-600">
              #{repo.rank_overall || 'N/A'}
            </div>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center gap-4 flex-wrap">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
              {repo.language}
            </span>
            {repo.uses_render && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                🚀 Built with Render
              </span>
            )}
            <span className="text-sm text-gray-500">
              Rank in {repo.language}: #{repo.rank_in_language}
            </span>
          </div>
        </div>

        <div className="mt-6">
          <a
            href={repo.repo_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-gray-900 text-white px-6 py-2 rounded hover:bg-gray-800"
          >
            View on GitHub →
          </a>
        </div>
      </div>

      {/* Render Integration (if applicable) */}
      {repo.uses_render && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-purple-900 mb-4">
            Render Integration
          </h2>
          <div className="grid md:grid-cols-3 gap-4 mb-4">
            <div>
              <div className="text-sm text-purple-600 font-medium mb-1">
                Category
              </div>
              <div className="text-lg font-semibold text-purple-900 capitalize">
                {repo.render_category || 'Community'}
              </div>
            </div>
            {repo.render_services && repo.render_services.length > 0 && (
              <div>
                <div className="text-sm text-purple-600 font-medium mb-1">
                  Services Used
                </div>
                <div className="flex flex-wrap gap-1">
                  {repo.render_services.map((service: string) => (
                    <span
                      key={service}
                      className="bg-purple-200 text-purple-900 text-xs px-2 py-1 rounded"
                    >
                      {service}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {repo.render_complexity_score && (
              <div>
                <div className="text-sm text-purple-600 font-medium mb-1">
                  Complexity Score
                </div>
                <div className="text-lg font-semibold text-purple-900">
                  {repo.render_complexity_score}/10
                </div>
              </div>
            )}
          </div>
          {repo.has_blueprint_button && (
            <div className="bg-white border border-purple-300 rounded p-3">
              <span className="text-sm text-green-600 font-medium">
                ✓ This project includes a Deploy to Render button
              </span>
            </div>
          )}
        </div>
      )}

      {/* Why It's Trending */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Why It's Trending
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          <div>
            <div className="text-3xl mb-2">⚡</div>
            <div className="text-sm text-gray-500 mb-1">Star Velocity</div>
            <div className="text-2xl font-bold text-gray-900">
              {repo.star_velocity?.toFixed(1)}%
            </div>
            <p className="text-sm text-gray-600 mt-1">
              Growth rate over last 7 days
            </p>
          </div>
          <div>
            <div className="text-3xl mb-2">📈</div>
            <div className="text-sm text-gray-500 mb-1">Activity Score</div>
            <div className="text-2xl font-bold text-gray-900">
              {repo.activity_score?.toFixed(1)}
            </div>
            <p className="text-sm text-gray-600 mt-1">
              {repo.commits_last_7_days} commits, {repo.issues_closed_last_7_days}{' '}
              issues closed
            </p>
          </div>
          <div>
            <div className="text-3xl mb-2">👥</div>
            <div className="text-sm text-gray-500 mb-1">Active Contributors</div>
            <div className="text-2xl font-bold text-gray-900">
              {repo.active_contributors}
            </div>
            <p className="text-sm text-gray-600 mt-1">
              Contributors in last 7 days
            </p>
          </div>
        </div>
      </div>

      {/* Historical Trends */}
      {snapshots.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Historical Trends
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Date
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Stars
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Momentum
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Rank
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Commits
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {snapshots.slice(0, 10).map((snapshot: any, index: number) => (
                  <tr key={index}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {new Date(snapshot.snapshot_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {snapshot.stars?.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-green-600">
                      {snapshot.momentum_score?.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      #{snapshot.rank_overall}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {snapshot.commits_last_7_days}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Similar Projects */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Similar Projects
        </h2>
        <p className="text-gray-600">
          Explore more {repo.language} projects in the{' '}
          <Link
            href={`/language/${repo.language}`}
            className="text-blue-600 hover:underline"
          >
            {repo.language} deep dive
          </Link>
          .
        </p>
      </div>
    </div>
  )
}
