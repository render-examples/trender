'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TaskTimeline } from '@/components/TaskTimeline'
import { workflowPanelContent } from '@/lib/content'

interface Task {
  name: string
  started_at: string
  completed_at: string | null
  status: string
  language?: string
  children?: Task[]
}

interface WorkflowRun {
  run_id: string
  started_at: string
  completed_at: string
  status: string
  task_tree: Task
  error_message: string | null
  repos_processed: number
  execution_time_seconds: number
}

export default function WorkflowPanel() {
  const [isExpanded, setIsExpanded] = useState(false)
  const [workflowRun, setWorkflowRun] = useState<WorkflowRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchWorkflowStatus = async () => {
      try {
        const response = await fetch('/api/workflow-status')
        if (!response.ok) {
          if (response.status === 404) {
            setError('No workflow runs yet')
          } else {
            throw new Error('Failed to fetch workflow status')
          }
          return
        }
        const data = await response.json()
        setWorkflowRun(data)
      } catch (err) {
        console.error('Error fetching workflow status:', err)
        setError('Failed to load workflow data')
      } finally {
        setLoading(false)
      }
    }

    fetchWorkflowStatus()
  }, [])

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'America/Los_Angeles',
      timeZoneName: 'short',
    })
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'completed': 'text-green-500',
      'failed': 'text-red-500',
      'running': 'text-yellow-500'
    }
    return colors[status] || 'text-yellow-500'
  }

  return (
    <div className="mt-8 bg-black">
      {/* Collapsible Header */}
      <div className="w-full px-6 py-4 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-3 transition-colors group cursor-pointer"
        >
          <svg
            className={`w-5 h-5 text-purple-400 transition-transform duration-300 ${
              isExpanded ? 'rotate-0' : '-rotate-90'
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          <span className="text-zinc-300 font-medium group-hover:text-purple-400 transition-colors">Learn more</span>
        </button>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="border border-zinc-700 px-4 sm:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6">
          {/* Why Workflows Section */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-white">{workflowPanelContent.title}</h3>
            <div className="space-y-3">
              {workflowPanelContent.paragraphs.map((paragraph, index) => (
                <p key={index} className="text-sm text-zinc-200 leading-relaxed">
                  {paragraph}
                </p>
              ))}
            </div>
          </div>

          {/* Latest Run Section */}
          {loading && (
            <div className="text-sm text-zinc-500">Loading workflow data...</div>
          )}

          {error && (
            <div className="text-sm text-zinc-500">{error}</div>
          )}

          {workflowRun && (
            <div className="space-y-6">
              {/* Workflows in Action Section */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold text-white">Workflows in action</h3>
                <p className="text-sm text-zinc-200">
                  Stats from the latest workflow runs powering Trender.
                </p>
              </div>

              {/* Run Metadata */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6 text-sm">
                <div>
                  <span className="text-zinc-400">Latest run:</span>{' '}
                  <span className="text-zinc-200">{formatDate(workflowRun.completed_at)}</span>
                </div>
                <div>
                  <span className="text-zinc-400">Duration:</span>{' '}
                  <span className="text-zinc-200">
                    {formatDuration(workflowRun.execution_time_seconds)}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-400">Repos processed:</span>{' '}
                  <span className="text-zinc-200">{workflowRun.repos_processed}</span>
                </div>
                <div>
                  <span className="text-zinc-400">Status:</span>{' '}
                  <span className={getStatusColor(workflowRun.status)}>
                    {workflowRun.status}
                  </span>
                </div>
              </div>

              {/* Timeline Visualization */}
              <div>
                <h4 className="text-xs sm:text-sm font-semibold text-zinc-200 mb-2 sm:mb-3 uppercase tracking-wider">
                  Execution Timeline
                </h4>
                <div className="bg-zinc-900 border border-zinc-800 p-2 sm:p-4">
                  <TaskTimeline
                    task={workflowRun.task_tree}
                    workflowStart={new Date(workflowRun.task_tree.started_at)}
                    totalDuration={workflowRun.execution_time_seconds}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

