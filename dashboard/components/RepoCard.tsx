'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { Repository } from '@/lib/db'

interface RepoCardProps {
  repo: Repository
}

export default function RepoCard({ repo }: RepoCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Get first ~500 chars of README for preview
  const readmePreview = repo.readme_content
    ? repo.readme_content.substring(0, 500) + (repo.readme_content.length > 500 ? '...' : '')
    : 'No README available'

  return (
    <motion.div
      layout
      className="flex-shrink-0 cursor-pointer"
      onClick={() => setIsExpanded(!isExpanded)}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      <motion.div
        layout
        className="bg-zinc-900 rounded-lg p-6 border-2 border-zinc-800 hover:border-white transition-colors"
        style={{ 
          width: isExpanded ? '600px' : '320px',
          minHeight: isExpanded ? 'auto' : '220px'
        }}
      >
        <div className="flex items-start justify-between mb-3">
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
            {repo.stars?.toLocaleString('en-US')}
          </span>
        </div>

        <motion.p 
          layout="position"
          className="text-sm text-zinc-400 mb-3"
        >
          {repo.description || 'No description available'}
        </motion.p>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="mt-4 pt-4 border-t border-zinc-800"
            >
              <h4 className="text-sm font-semibold text-white mb-2">README Preview</h4>
              <div className="text-xs text-zinc-400 max-h-60 overflow-y-auto prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{readmePreview}</ReactMarkdown>
              </div>
              <a
                href={repo.repo_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-3 text-xs text-blue-400 hover:text-blue-300"
                onClick={(e) => e.stopPropagation()}
              >
                View on GitHub →
              </a>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  )
}
