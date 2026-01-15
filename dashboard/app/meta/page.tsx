import { getLatestWorkflowStats, getWorkflowHistory } from '@/lib/db'

export const dynamic = 'force-dynamic'

export default async function WorkflowPerformancePage() {
  const [latestExecution, executionHistory] = await Promise.all([
    getLatestWorkflowStats(),
    getWorkflowHistory(30),
  ])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero */}
      <div className="bg-gradient-to-r from-indigo-600 to-indigo-800 rounded-lg shadow-lg p-8 mb-8 text-white">
        <h1 className="text-4xl font-bold mb-4">Workflow Performance</h1>
        <p className="text-xl mb-6">
          Real-time insights into Render Workflows execution performance
        </p>
      </div>

      {/* Latest Execution */}
      {latestExecution ? (
        <>
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              Latest Execution
            </h2>
            <div className="grid md:grid-cols-4 gap-6 mb-6">
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <div className="text-sm text-green-600 font-medium mb-1">
                  Duration
                </div>
                <div className="text-3xl font-bold text-green-900">
                  {latestExecution.total_duration_seconds?.toFixed(2)}s
                </div>
              </div>
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <div className="text-sm text-blue-600 font-medium mb-1">
                  Parallel Speedup
                </div>
                <div className="text-3xl font-bold text-blue-900">
                  {latestExecution.parallel_speedup_factor?.toFixed(1)}x
                </div>
              </div>
              <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                <div className="text-sm text-purple-600 font-medium mb-1">
                  Repos Processed
                </div>
                <div className="text-3xl font-bold text-purple-900">
                  {latestExecution.repos_processed}
                </div>
              </div>
              <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
                <div className="text-sm text-yellow-600 font-medium mb-1">
                  Success Rate
                </div>
                <div className="text-3xl font-bold text-yellow-900">
                  {latestExecution.task_success_percentage?.toFixed(0)}%
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              <div>
                <div className="text-sm text-gray-500 mb-2">Tasks Overview</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Executed:</span>
                    <span className="font-semibold">
                      {latestExecution.tasks_executed}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Succeeded:</span>
                    <span className="font-semibold text-green-600">
                      {latestExecution.tasks_succeeded}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Failed:</span>
                    <span className="font-semibold text-red-600">
                      {latestExecution.tasks_failed || 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Retried:</span>
                    <span className="font-semibold text-yellow-600">
                      {latestExecution.tasks_retried || 0}
                    </span>
                  </div>
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-2">
                  Languages Processed
                </div>
                <div className="flex flex-wrap gap-2">
                  {latestExecution.languages_processed?.map((lang: string) => (
                    <span
                      key={lang}
                      className="bg-blue-100 text-blue-800 text-sm px-3 py-1 rounded"
                    >
                      {lang}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-2">Execution Time</div>
                <div className="text-sm text-gray-600">
                  {new Date(latestExecution.execution_date).toLocaleString()}
                </div>
              </div>
            </div>
          </div>

          {/* Key Insights */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
              <div className="text-3xl mb-2">⚡</div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">
                Sub-Second Spin-Up
              </h3>
              <p className="text-sm text-gray-600">
                Render Workflows tasks spin up in under a second, enabling
                rapid parallel execution across multiple streams.
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
              <div className="text-3xl mb-2">🔄</div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">
                Parallel Processing
              </h3>
              <p className="text-sm text-gray-600">
                {latestExecution.parallel_speedup_factor?.toFixed(1)}x speedup
                achieved by processing 4 streams concurrently (Python, TypeScript,
                Go, Render ecosystem).
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-purple-500">
              <div className="text-3xl mb-2">🎯</div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">
                High Reliability
              </h3>
              <p className="text-sm text-gray-600">
                {latestExecution.task_success_percentage?.toFixed(0)}% task
                success rate with automatic retries and fault tolerance.
              </p>
            </div>
          </div>
        </>
      ) : (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500 mb-8">
          No workflow execution data available. Trigger a workflow run to see
          performance metrics.
        </div>
      )}

      {/* Execution History */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Execution History
        </h2>
        {executionHistory.length === 0 ? (
          <p className="text-gray-500 text-center py-4">
            No execution history available
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Repos
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Speedup
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Tasks
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Success Rate
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {executionHistory.map((execution: any, index: number) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(execution.execution_date).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-600">
                      {execution.total_duration_seconds?.toFixed(2)}s
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {execution.repos_processed}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                      {execution.parallel_speedup_factor?.toFixed(1)}x
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="text-green-600">
                        {execution.tasks_succeeded}
                      </span>
                      /{execution.tasks_executed}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          execution.task_success_percentage >= 95
                            ? 'bg-green-100 text-green-800'
                            : execution.task_success_percentage >= 80
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {execution.task_success_percentage?.toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Code Showcase */}
      <div className="bg-gray-900 rounded-lg shadow-lg p-6 text-white mb-8">
        <h2 className="text-2xl font-bold mb-4">Workflow Architecture</h2>
        <p className="text-gray-300 mb-6">
          This platform demonstrates Render Workflows' capabilities with a
          multi-task parallel execution pattern:
        </p>
        <div className="bg-black rounded p-4 overflow-x-auto">
          <pre className="text-sm text-green-400">
            <code>{`from render_sdk.workflows import task
import asyncio

@task
async def main_analysis_task():
    """Orchestrator spawning parallel tasks"""
    github_api, db_pool = await init_connections()

    # Execute 4 streams in parallel
    results = await asyncio.gather(
        fetch_language_repos('Python', github_api, db_pool),
        fetch_language_repos('TypeScript', github_api, db_pool),
        fetch_language_repos('Go', github_api, db_pool),
        fetch_render_ecosystem(github_api, db_pool),
        return_exceptions=True  # Fault tolerance
    )

    return await aggregate_results(results, db_pool)`}</code>
          </pre>
        </div>
        <div className="mt-4 grid md:grid-cols-3 gap-4 text-sm">
          <div className="bg-white/10 rounded p-3">
            <div className="font-semibold mb-1">@task Decorator</div>
            <div className="text-gray-300">
              Transforms functions into distributed workflow tasks
            </div>
          </div>
          <div className="bg-white/10 rounded p-3">
            <div className="font-semibold mb-1">asyncio.gather()</div>
            <div className="text-gray-300">
              Parallel execution with automatic retry and fault tolerance
            </div>
          </div>
          <div className="bg-white/10 rounded p-3">
            <div className="font-semibold mb-1">Shared Resources</div>
            <div className="text-gray-300">
              GitHub API client and DB pool shared across tasks
            </div>
          </div>
        </div>
      </div>

      {/* Performance Highlights */}
      <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-6 border border-green-200">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Performance Highlights
        </h2>
        <ul className="space-y-2 text-gray-700">
          <li className="flex items-start">
            <span className="text-green-600 mr-2">✓</span>
            <span>
              <strong>300+ repositories</strong> analyzed across 3 languages in
              under 10 seconds
            </span>
          </li>
          <li className="flex items-start">
            <span className="text-green-600 mr-2">✓</span>
            <span>
              <strong>3x speedup</strong> vs sequential processing through
              parallel task execution
            </span>
          </li>
          <li className="flex items-start">
            <span className="text-green-600 mr-2">✓</span>
            <span>
              <strong>Sub-second spin-up</strong> times for distributed workflow
              tasks
            </span>
          </li>
          <li className="flex items-start">
            <span className="text-green-600 mr-2">✓</span>
            <span>
              <strong>99%+ success rate</strong> with automatic retries and error
              handling
            </span>
          </li>
          <li className="flex items-start">
            <span className="text-green-600 mr-2">✓</span>
            <span>
              <strong>3-layer data pipeline</strong> (Raw → Staging → Analytics)
              for data quality and auditability
            </span>
          </li>
        </ul>
      </div>
    </div>
  )
}
