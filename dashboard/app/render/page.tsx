import Link from 'next/link'
import { getRenderShowcase, getEcosystemStats } from '@/lib/db'

export const dynamic = 'force-dynamic'

export default async function RenderShowcase() {
  const [renderProjects, ecosystemStats] = await Promise.all([
    getRenderShowcase(50),
    getEcosystemStats(),
  ])

  // Group projects by category
  const officialProjects = renderProjects.filter(
    (p: any) => p.render_category === 'official'
  )
  const communityProjects = renderProjects.filter(
    (p: any) => p.render_category === 'community'
  )
  const employeeProjects = renderProjects.filter(
    (p: any) => p.render_category === 'employee'
  )
  const blueprints = renderProjects.filter(
    (p: any) => p.render_category === 'blueprint'
  )

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero */}
      <div className="bg-gradient-to-r from-purple-600 to-purple-800 rounded-lg shadow-lg p-8 mb-8 text-white">
        <h1 className="text-4xl font-bold mb-4">Built with Render</h1>
        <p className="text-xl mb-6">
          Discover amazing projects leveraging Render's infrastructure
        </p>

        {/* Ecosystem Stats */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-6">
          <div className="bg-white/10 rounded p-4">
            <div className="text-3xl font-bold">
              {ecosystemStats.total_projects}
            </div>
            <div className="text-sm opacity-90">Total Projects</div>
          </div>
          <div className="bg-white/10 rounded p-4">
            <div className="text-3xl font-bold">
              {ecosystemStats.total_stars?.toLocaleString()}
            </div>
            <div className="text-sm opacity-90">Total Stars</div>
          </div>
          <div className="bg-white/10 rounded p-4">
            <div className="text-3xl font-bold">
              {ecosystemStats.by_category?.length || 0}
            </div>
            <div className="text-sm opacity-90">Categories</div>
          </div>
        </div>
      </div>

      {/* Official Blueprints */}
      {officialProjects.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Official Blueprints
            </h2>
            <span className="text-sm text-gray-500">
              {officialProjects.length} projects
            </span>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {officialProjects.slice(0, 10).map((project: any) => (
              <ProjectCard key={project.repo_full_name} project={project} />
            ))}
          </div>
        </section>
      )}

      {/* Community Stars */}
      {communityProjects.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Community Stars</h2>
            <span className="text-sm text-gray-500">
              {communityProjects.length} projects
            </span>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {communityProjects.slice(0, 15).map((project: any) => (
              <ProjectCard key={project.repo_full_name} project={project} />
            ))}
          </div>
        </section>
      )}

      {/* Employee Innovation */}
      {employeeProjects.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Employee Innovation
            </h2>
            <span className="text-sm text-gray-500">
              {employeeProjects.length} projects
            </span>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {employeeProjects.slice(0, 10).map((project: any) => (
              <ProjectCard key={project.repo_full_name} project={project} />
            ))}
          </div>
        </section>
      )}

      {/* Blueprint Showcase */}
      {blueprints.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Blueprint Showcase
            </h2>
            <span className="text-sm text-gray-500">
              {blueprints.length} blueprints
            </span>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {blueprints.map((project: any) => (
              <ProjectCard
                key={project.repo_full_name}
                project={project}
                showBlueprint
              />
            ))}
          </div>
        </section>
      )}

      {/* Workflow Showcase Meta */}
      <section className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-blue-900 mb-4">
          Trender: Workflow Showcase
        </h2>
        <p className="text-gray-700 mb-4">
          This project itself is a meta-example of Render Workflows in action!
          It demonstrates parallel task execution, sub-second spin-up times,
          and distributed data processing.
        </p>
        <Link
          href="/meta"
          className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          View Performance Metrics →
        </Link>
      </section>
    </div>
  )
}

function ProjectCard({
  project,
  showBlueprint = false,
}: {
  project: any
  showBlueprint?: boolean
}) {
  return (
    <Link
      href={`/repo/${project.repo_full_name}`}
      className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6 border border-gray-200"
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-sm font-medium text-purple-600">
          {project.language}
        </span>
        <span className="text-sm text-gray-500">
          ⭐ {project.stars?.toLocaleString()}
        </span>
      </div>

      <h3 className="font-bold text-gray-900 mb-2">{project.repo_full_name}</h3>
      <p className="text-sm text-gray-600 mb-4 line-clamp-2">
        {project.description || 'No description available'}
      </p>

      {/* Render Services */}
      {project.render_services && project.render_services.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {project.render_services.slice(0, 3).map((service: string) => (
            <span
              key={service}
              className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded"
            >
              {service}
            </span>
          ))}
          {project.render_services.length > 3 && (
            <span className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded">
              +{project.render_services.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-gray-500">Momentum</div>
          <div className="font-semibold">
            {project.momentum_score?.toFixed(1)}
          </div>
        </div>
        <div>
          <div className="text-gray-500">
            {showBlueprint ? 'Complexity' : 'Activity'}
          </div>
          <div className="font-semibold">
            {showBlueprint
              ? project.render_complexity_score || 'N/A'
              : project.activity_score?.toFixed(1)}
          </div>
        </div>
      </div>

      {showBlueprint && project.has_blueprint_button && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <span className="text-xs text-green-600 font-medium">
            ✓ Deploy Button Available
          </span>
        </div>
      )}
    </Link>
  )
}
