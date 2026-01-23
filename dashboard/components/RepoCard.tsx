'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { Repository } from '@/lib/db'
import { formatStarCount } from '@/lib/formatters'

interface RepoCardProps {
  repo: Repository
}

export default function RepoCard({ repo }: RepoCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Get first ~500 chars of README for preview
  const readmePreview = repo.readme_content
    ? repo.readme_content.substring(0, 500) + (repo.readme_content.length > 500 ? '...' : '')
    : 'Not available'

  return (
    <motion.div
      layout
      className="flex-shrink-0 cursor-pointer"
      onClick={() => setIsExpanded(!isExpanded)}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ 
        layout: { duration: 0.3, ease: "easeInOut" },
        opacity: { duration: 0.2 }
      }}
    >
      <motion.div
        layout
        className="bg-black p-6 border border-zinc-700 hover:border-white transition-colors flex flex-col"
        style={{ 
          width: isExpanded ? '600px' : '320px',
          height: '220px'
        }}
      >
        <div className="flex items-start justify-between mb-3 flex-shrink-0">
          <motion.h3 
            layout="position"
            className="text-lg font-semibold text-white truncate pr-2"
          >
            {repo.repo_full_name}
          </motion.h3>
          <span className="text-yellow-400 flex items-center gap-1 flex-shrink-0">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            {formatStarCount(repo.stars)}
          </span>
        </div>

        <motion.p 
          layout="position"
          className="text-sm text-zinc-400 mb-3 flex-shrink-0"
        >
          {repo.description || 'No description available'}
        </motion.p>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="mt-4 pt-4 flex-1 flex flex-col overflow-hidden"
            >
              <h4 className="text-sm font-semibold text-white mb-2 flex-shrink-0">README</h4>
              <div className="text-xs text-zinc-400 overflow-y-auto prose prose-invert prose-sm max-w-none flex-1">
                <ReactMarkdown>{readmePreview}</ReactMarkdown>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  )
}
