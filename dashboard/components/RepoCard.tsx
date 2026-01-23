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

  const handleCardClick = () => {
    if (isExpanded) {
      // Open GitHub URL in new tab when expanded
      window.open(repo.repo_url, '_blank', 'noopener,noreferrer')
    } else {
      // Toggle expansion when collapsed
      setIsExpanded(true)
    }
  }

  // Show more content when expanded for better scrolling
  const readmeContent = repo.readme_content || 'Not available'

  return (
    <motion.div
      layout
      className="flex-shrink-0 cursor-pointer"
      onClick={handleCardClick}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ 
        layout: { duration: 0.3, ease: "easeInOut" },
        opacity: { duration: 0.2 }
      }}
    >
      <motion.div
        layout
        className="bg-black p-6 border border-zinc-700 hover:border-white transition-colors flex flex-col relative"
        style={{ 
          width: isExpanded ? '600px' : '380px',
          height: '280px'
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
              className="mt-4 pt-4 border-t border-zinc-700 flex-1 flex flex-col overflow-hidden"
            >
              <h4 className="text-sm font-semibold text-white mb-2 flex-shrink-0">README</h4>
              <div className="text-xs text-zinc-400 overflow-y-auto prose prose-invert prose-sm max-w-none flex-1 pr-2">
                <ReactMarkdown>{readmeContent}</ReactMarkdown>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Arrow icon in bottom right when expanded */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.2 }}
              className="absolute bottom-4 right-4 text-zinc-400 hover:text-white transition-colors"
            >
              <svg 
                className="w-5 h-5" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" 
                />
              </svg>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  )
}
