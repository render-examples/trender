import Link from 'next/link'
import { getLanguageTopRepos, getLanguageStats } from '@/lib/db'

export const dynamic = 'force-dynamic'

const LANGUAGES = ['Python', 'TypeScript', 'Go']

export default async function LanguagePage({
  params,
}: {
  params: { lang: string }
}) {
  const language = params.lang

  // Validate language
  if (!LANGUAGES.includes(language)) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h1 className="text-2xl font-bold text-red-900 mb-2">
            Language Not Found
          </h1>
          <p className="text-red-700 mb-4">
            The language "{language}" is not currently tracked.
          </p>
          <div className="flex gap-2 justify-center">
            {LANGUAGES.map((lang) => (
              <Link
                key={lang}
                href={`/language/${lang}`}
                className="text-blue-600 hover:underline"
              >
                {lang}
              </Link>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const [repos, languageStats] = await Promise.all([
    getLanguageTopRepos(language, 50),
    getLanguageStats(),
  ])

  const currentLangStats = languageStats.find(
    (s: any) => s.language_name === language
  )

  const renderRepos = repos.filter((r: any) => r.uses_render)

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Language Header */}
      <div className="bg-gradient-to-r from-green-600 to-green-800 rounded-lg shadow-lg p-8 mb-8 text-white">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-4xl font-bold">{language}</h1>
          <div className="flex gap-2">
            {LANGUAGES.map((lang) => (
              <Link
                key={lang}
                href={`/language/${lang}`}
                className={`px-3 py-1 rounded ${
                  lang === language
                    ? 'bg-white text-green-800 font-medium'
                    : 'bg-white/20 hover:bg-white/30'
                }`}
              >
                {lang}
              </Link>
            ))}
          </div>
        </div>
        <p className="text-xl mb-6">
          Deep dive into the {language} ecosystem
        </p>

        {/* Language Stats */}
        {currentLangStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div className="bg-white/10 rounded p-4">
              <div className="text-3xl font-bold">
                {currentLangStats.total_repos}
              </div>
              <div className="text-sm opacity-90">Tracked Repos</div>
            </div>
            <div className="bg-white/10 rounded p-4">
              <div className="text-3xl font-bold">
                {currentLangStats.total_stars?.toLocaleString()}
              </div>
              <div className="text-sm opacity-90">Total Stars</div>
            </div>
            <div className="bg-white/10 rounded p-4">
              <div className="text-3xl font-bold">
                {currentLangStats.avg_momentum?.toFixed(1)}
              </div>
              <div className="text-sm opacity-90">Avg Momentum</div>
            </div>
            <div className="bg-white/10 rounded p-4">
              <div className="text-3xl font-bold">
                {currentLangStats.render_adoption_percentage?.toFixed(0)}%
              </div>
              <div className="text-sm opacity-90">Render Adoption</div>
            </div>
          </div>
        )}
      </div>

      {/* Render Projects in this Language */}
      {renderRepos.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {language} Projects Using Render
            </h2>
            <span className="text-sm text-purple-600 font-medium">
              {renderRepos.length} projects
            </span>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {renderRepos.slice(0, 6).map((repo: any) => (
              <RepoCard key={repo.repo_full_name} repo={repo} highlight />
            ))}
          </div>
        </section>
      )}

      {/* Top 50 Repositories */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            Top 50 {language} Repositories
          </h2>
          <span className="text-sm text-gray-500">{repos.length} repos</span>
        </div>

        {repos.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
            No repositories found for {language}. Trigger a workflow run to
            populate data.
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rank
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Repository
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Stars
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Momentum
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Activity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Render
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {repos.map((repo: any, index: number) => (
                  <tr key={repo.repo_full_name} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      #{repo.rank_in_language || index + 1}
                    </td>
                    <td className="px-6 py-4">
                      <Link
                        href={`/repo/${repo.repo_full_name}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {repo.repo_full_name}
                      </Link>
                      <p className="text-sm text-gray-500 line-clamp-1">
                        {repo.description}
                      </p>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {repo.stars?.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {repo.momentum_score?.toFixed(1)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center gap-1">
                        <span>↑ {repo.commits_last_7_days}</span>
                        <span className="text-gray-400">|</span>
                        <span>👥 {repo.active_contributors}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {repo.uses_render ? (
                        <span className="bg-purple-100 text-purple-800 text-xs font-medium px-2 py-1 rounded">
                          ✓
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

function RepoCard({ repo, highlight = false }: { repo: any; highlight?: boolean }) {
  return (
    <Link
      href={`/repo/${repo.repo_full_name}`}
      className={`rounded-lg shadow hover:shadow-lg transition-shadow p-6 border ${
        highlight
          ? 'bg-purple-50 border-purple-200'
          : 'bg-white border-gray-200'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-2xl font-bold text-gray-400">
          #{repo.rank_in_language}
        </span>
        <span className="text-sm text-gray-500">
          ⭐ {repo.stars?.toLocaleString()}
        </span>
      </div>

      <h3 className="text-lg font-bold text-gray-900 mb-2">
        {repo.repo_full_name}
      </h3>
      <p className="text-sm text-gray-600 mb-4 line-clamp-2">
        {repo.description || 'No description available'}
      </p>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div className="text-gray-500">Momentum</div>
          <div className="font-semibold">{repo.momentum_score?.toFixed(1)}</div>
        </div>
        <div>
          <div className="text-gray-500">Commits</div>
          <div className="font-semibold">{repo.commits_last_7_days}</div>
        </div>
        <div>
          <div className="text-gray-500">Contributors</div>
          <div className="font-semibold">{repo.active_contributors}</div>
        </div>
      </div>
    </Link>
  )
}
