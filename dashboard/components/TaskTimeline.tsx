'use client'

import { motion } from 'framer-motion'

interface Task {
  name: string
  started_at: string
  completed_at: string | null
  status: string
  language?: string
  children?: Task[]
}

interface TaskTimelineProps {
  task: Task
  workflowStart: Date
  totalDuration: number
}

export function TaskTimeline({ task, workflowStart, totalDuration }: TaskTimelineProps) {
  const getTaskColor = (taskName: string) => {
    if (taskName === 'main_analysis_task') return 'bg-purple-500'
    if (taskName === 'fetch_language_repos') return 'bg-blue-500'
    if (taskName === 'fetch_render_repos') return 'bg-pink-500'
    if (taskName === 'analyze_repo_batch') return 'bg-cyan-500'
    if (taskName === 'aggregate_results') return 'bg-green-500'
    if (taskName === 'cleanup_old_data') return 'bg-yellow-500'
    return 'bg-zinc-500'
  }

  const getTaskLabel = (task: Task) => {
    if (task.language) {
      return `${task.name} (${task.language})`
    }
    return task.name
  }

  const calculateBarPosition = (startedAt: string, completedAt: string | null) => {
    const start = new Date(startedAt)
    const end = completedAt ? new Date(completedAt) : new Date()
    
    const startOffset = (start.getTime() - workflowStart.getTime()) / 1000
    const duration = (end.getTime() - start.getTime()) / 1000
    
    const leftPercent = (startOffset / totalDuration) * 100
    const widthPercent = (duration / totalDuration) * 100
    
    const mins = Math.floor(duration / 60)
    const secs = Math.floor(duration % 60)
    const formattedDuration = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
    
    return {
      left: `${Math.max(0, leftPercent)}%`,
      width: `${Math.min(100 - leftPercent, widthPercent)}%`,
      duration: formattedDuration,
    }
  }

  const renderTaskBar = (task: Task, depth: number = 0) => {
    const barPosition = calculateBarPosition(task.started_at, task.completed_at)
    const color = getTaskColor(task.name)
    const label = getTaskLabel(task)
    
    return (
      <div key={`${task.name}-${task.language || 'main'}`} className="mb-2">
        {/* Desktop/Tablet: Horizontal Layout */}
        <div className="hidden sm:flex items-center gap-1.5">
          {/* Task Name - Left */}
          <span 
            className="text-xs text-zinc-200 font-mono flex-shrink-0 whitespace-nowrap overflow-hidden text-ellipsis sm:min-w-[180px] sm:max-w-[180px] md:min-w-[300px] md:max-w-[300px]"
            style={{ paddingLeft: `${depth * 16}px` }}
            title={label}
          >
            {label}
          </span>
          
          {/* Duration - Middle */}
          <span className="text-xs text-zinc-400 flex-shrink-0 w-16 text-right">
            {barPosition.duration}
          </span>
          
          {/* Timeline Bar - Right */}
          <div className="relative h-6 bg-zinc-800 border border-zinc-700 overflow-hidden flex-1">
            <motion.div
              className={`absolute top-0 h-full ${color}`}
              initial={{ width: 0, left: barPosition.left }}
              animate={{ width: barPosition.width, left: barPosition.left }}
              transition={{ duration: 1.5, ease: 'easeOut' }}
            />
          </div>
        </div>

        {/* Mobile: Stacked Layout */}
        <div className="sm:hidden">
          {/* Task Name + Duration Row */}
          <div 
            className="flex items-center justify-between gap-2 mb-1"
            style={{ paddingLeft: `${depth * 8}px` }}
          >
            <span 
              className="text-[10px] text-zinc-200 font-mono flex-1 truncate"
              title={label}
            >
              {label}
            </span>
            <span className="text-[10px] text-zinc-400 flex-shrink-0">
              {barPosition.duration}
            </span>
          </div>
          
          {/* Timeline Bar Row */}
          <div 
            className="relative h-5 bg-zinc-800 border border-zinc-700 overflow-hidden"
            style={{ marginLeft: `${depth * 8}px` }}
          >
            <motion.div
              className={`absolute top-0 h-full ${color}`}
              initial={{ width: 0, left: barPosition.left }}
              animate={{ width: barPosition.width, left: barPosition.left }}
              transition={{ duration: 1.5, ease: 'easeOut' }}
            />
          </div>
        </div>

        {task.children && task.children.length > 0 && (
          <div className="mt-1">
            {task.children.map((child) => renderTaskBar(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {renderTaskBar(task)}
    </div>
  )
}

