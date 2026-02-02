'use client'

import { useState } from 'react'

/**
 * Represents a single task in the workflow execution tree
 */
interface Task {
  name: string
  started_at: string
  completed_at: string | null
  status: string
  language?: string
  children?: Task[]
}

interface TaskTreeProps {
  task: Task
  depth?: number
}

/**
 * TaskTree Component
 * 
 * Displays a hierarchical, collapsible tree view of workflow task execution.
 * Shows task status, name, language (if applicable), and duration.
 * 
 * Features:
 * - Collapsible parent tasks with expand/collapse icons
 * - Status icons (✓ completed, ⚠ failed, ↻ running)
 * - Duration display in seconds
 * - Indentation to show task hierarchy
 * - Hover effects for better UX
 */
export function TaskTree({ task, depth = 0 }: TaskTreeProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  
  const hasChildren = task.children && task.children.length > 0
  
  /**
   * Get the appropriate icon based on task status
   */
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="text-green-500">✓</span>
      case 'failed':
        return <span className="text-red-500">⚠</span>
      case 'running':
        return <span className="text-yellow-500">↻</span>
      default:
        return <span className="text-zinc-500">•</span>
    }
  }
  
  /**
   * Calculate task duration in seconds
   * Returns null if task hasn't completed yet
   */
  const calculateDuration = (startedAt: string, completedAt: string | null): string | null => {
    if (!completedAt) return null
    const start = new Date(startedAt)
    const end = new Date(completedAt)
    const duration = (end.getTime() - start.getTime()) / 1000
    return duration.toFixed(1)
  }
  
  const duration = calculateDuration(task.started_at, task.completed_at)
  const taskLabel = task.language ? `${task.name} (${task.language})` : task.name
  
  return (
    <div className="text-sm">
      {/* Task row with status, name, and duration */}
      <div
        className="flex items-center gap-2 py-1 hover:bg-zinc-800/50 cursor-pointer"
        style={{ paddingLeft: `${depth * 16}px` }}
        onClick={() => hasChildren && setIsExpanded(!isExpanded)}
      >
        {/* Expand/collapse arrow (only for parent tasks) */}
        {hasChildren && (
          <svg
            className={`w-3 h-3 text-zinc-500 transition-transform ${isExpanded ? '' : '-rotate-90'}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        )}
        {!hasChildren && <span className="w-3" />}
        
        {/* Status icon */}
        {getStatusIcon(task.status)}
        
        {/* Task name/label */}
        <span className="font-mono text-zinc-300">{taskLabel}</span>
        
        {/* Duration (if completed) */}
        {duration && (
          <span className="text-zinc-600 text-xs ml-auto">{duration}s</span>
        )}
      </div>
      
      {/* Recursively render child tasks */}
      {hasChildren && isExpanded && (
        <div>
          {task.children!.map((child, idx) => (
            <TaskTree
              key={`${child.name}-${child.language || idx}`}
              task={child}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

