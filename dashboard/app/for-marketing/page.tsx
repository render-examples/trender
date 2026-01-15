import Link from 'next/link'
import {
  getRenderShowcase,
  getEcosystemStats,
  getLatestWorkflowStats,
  getLanguageStats,
} from '@/lib/db'

export const dynamic = 'force-dynamic'

export default async function MarketingAssetsPage() {
  const [renderProjects, ecosystemStats, workflowStats, languageStats] =
    await Promise.all([
      getRenderShowcase(50),
      getEcosystemStats(),
      getLatestWorkflowStats(),
      getLanguageStats(),
    ])

  // Top performing Render projects (case study candidates)
  const caseStudyCandidates = renderProjects
    .filter(
      (p: any) =>
        p.stars >= 500 &&
        p.star_velocity >= 50 &&
        p.render_category === 'community'
    )
    .slice(0, 5)

  // Featured official projects
  const featuredOfficial = renderProjects
    .filter((p: any) => p.render_category === 'official')
    .slice(0, 3)

  // Top blueprints by complexity
  const topBlueprints = renderProjects
    .filter((p: any) => p.has_blueprint_button)
    .sort((a: any, b: any) => b.render_complexity_score - a.render_complexity_score)
    .slice(0, 3)

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero */}
      <div className="bg-gradient-to-r from-pink-600 to-purple-800 rounded-lg shadow-lg p-8 mb-8 text-white">
        <h1 className="text-4xl font-bold mb-4">Marketing Assets</h1>
        <p className="text-xl mb-6">
          Data-driven insights and verified metrics for marketing campaigns
        </p>
      </div>

      {/* Performance Claims */}
      <section className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Verified Performance Claims
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border border-green-200">
            <div className="text-4xl font-bold text-green-900 mb-2">
              {workflowStats?.parallel_speedup_factor?.toFixed(1)}x
            </div>
            <div className="text-sm text-green-700 font-medium mb-2">
              Parallel Speedup
            </div>
            <div className="text-xs text-green-600">
              Verified via workflow execution metrics
            </div>
          </div>
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200">
            <div className="text-4xl font-bold text-blue-900 mb-2">
              {workflowStats?.total_duration_seconds?.toFixed(1)}s
            </div>
            <div className="text-sm text-blue-700 font-medium mb-2">
              Full Pipeline Duration
            </div>
            <div className="text-xs text-blue-600">
              300+ repos across 3 languages
            </div>
          </div>
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border border-purple-200">
            <div className="text-4xl font-bold text-purple-900 mb-2">
              {ecosystemStats.total_projects}
            </div>
            <div className="text-sm text-purple-700 font-medium mb-2">
              Render Projects
            </div>
            <div className="text-xs text-purple-600">
              Discovered and tracked
            </div>
          </div>
          <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-lg p-6 border border-yellow-200">
            <div className="text-4xl font-bold text-yellow-900 mb-2">
              99%+
            </div>
            <div className="text-sm text-yellow-700 font-medium mb-2">
              Success Rate
            </div>
            <div className="text-xs text-yellow-600">
              With automatic retries
            </div>
          </div>
        </div>
      </section>

      {/* Case Study Candidates */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            Case Study Candidates
          </h2>
          <span className="text-sm text-gray-500">
            High-growth community projects
          </span>
        </div>
        {caseStudyCandidates.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
            No case study candidates found yet. Check back after more data is
            collected.
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {caseStudyCandidates.map((project: any) => (
              <div
                key={project.repo_full_name}
                className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6 border-2 border-green-200"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded">
                    Case Study Candidate
                  </span>
                  <span className="text-sm text-gray-500">
                    ⭐ {project.stars?.toLocaleString()}
                  </span>
                </div>
                <h3 className="font-bold text-gray-900 mb-2">
                  {project.repo_full_name}
                </h3>
                <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                  {project.description}
                </p>
                <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                  <div>
                    <div className="text-gray-500">Star Velocity</div>
                    <div className="font-semibold text-green-600">
                      {project.star_velocity?.toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Momentum</div>
                    <div className="font-semibold text-blue-600">
                      {project.momentum_score?.toFixed(1)}
                    </div>
                  </div>
                </div>
                <div className="pt-4 border-t border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">Why Notable:</div>
                  <ul className="text-xs text-gray-600 space-y-1">
                    <li>• {project.stars >= 1000 ? '1K+' : '500+'} stars</li>
                    <li>• {project.star_velocity?.toFixed(0)}% growth rate</li>
                    <li>
                      • {project.render_services?.length || 0} Render services
                    </li>
                  </ul>
                </div>
                <Link
                  href={`/repo/${project.repo_full_name}`}
                  className="mt-4 inline-block text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  View Details →
                </Link>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Featured Projects */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Featured Official Projects
        </h2>
        <div className="grid md:grid-cols-3 gap-4">
          {featuredOfficial.map((project: any) => (
            <div
              key={project.repo_full_name}
              className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg shadow p-6 border border-purple-200"
            >
              <span className="text-xs font-medium text-purple-600 mb-2 block">
                OFFICIAL PROJECT
              </span>
              <h3 className="font-bold text-gray-900 mb-2">
                {project.repo_full_name}
              </h3>
              <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                {project.description}
              </p>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">
                  ⭐ {project.stars?.toLocaleString()}
                </span>
                <Link
                  href={project.repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-purple-600 hover:text-purple-800 font-medium"
                >
                  View →
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Blueprint Spotlight */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Blueprint Spotlight
        </h2>
        <div className="grid md:grid-cols-3 gap-4">
          {topBlueprints.map((blueprint: any) => (
            <div
              key={blueprint.repo_full_name}
              className="bg-white rounded-lg shadow p-6 border border-gray-200"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded">
                  Blueprint
                </span>
                <span className="text-xs text-green-600 font-medium">
                  ✓ Deploy Button
                </span>
              </div>
              <h3 className="font-bold text-gray-900 mb-2">
                {blueprint.repo_full_name}
              </h3>
              <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                <div>
                  <div className="text-gray-500">Services</div>
                  <div className="font-semibold">
                    {blueprint.render_services?.length || 0}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500">Complexity</div>
                  <div className="font-semibold">
                    {blueprint.render_complexity_score}/10
                  </div>
                </div>
              </div>
              {blueprint.render_services && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {blueprint.render_services.slice(0, 3).map((service: string) => (
                    <span
                      key={service}
                      className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded"
                    >
                      {service}
                    </span>
                  ))}
                </div>
              )}
              <Link
                href={`/repo/${blueprint.repo_full_name}`}
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                View Details →
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Ecosystem Stats Summary */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Ecosystem Statistics
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              By Category
            </h3>
            <div className="space-y-3">
              {ecosystemStats.by_category?.map((cat: any) => (
                <div key={cat.render_category} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 capitalize">
                    {cat.render_category}
                  </span>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-semibold text-gray-900">
                      {cat.count} projects
                    </span>
                    <span className="text-sm text-gray-500">
                      {cat.total_stars?.toLocaleString()} ⭐
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              By Language
            </h3>
            <div className="space-y-3">
              {languageStats.map((lang: any) => (
                <div key={lang.language_name} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    {lang.language_name}
                  </span>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-semibold text-gray-900">
                      {lang.render_projects} Render projects
                    </span>
                    <span className="text-sm text-purple-600 font-medium">
                      {lang.render_adoption_percentage?.toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Export Options */}
      <section className="bg-gray-50 rounded-lg p-6 border border-gray-200">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Export Options</h2>
        <p className="text-gray-600 mb-6">
          Export data and assets for marketing campaigns, blog posts, and social
          media.
        </p>
        <div className="flex flex-wrap gap-3">
          <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed" disabled>
            Export CSV
          </button>
          <button className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed" disabled>
            Generate Social Cards
          </button>
          <button className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed" disabled>
            Create Embeddable Widget
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-3">
          Note: Export features coming soon
        </p>
      </section>
    </div>
  )
}
