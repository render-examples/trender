'use client'

import { useMemo, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Repository } from '@/lib/db'
import { renderMarkdown } from '@/lib/markdown'

interface ReadmePanelProps {
  repo: Repository
  onClose: () => void
}

export default function ReadmePanel({ repo, onClose }: ReadmePanelProps) {
  const contentRef = useRef<HTMLDivElement>(null)
  
  // Render full markdown content (not truncated)
  const renderedReadme = useMemo(() => {
    const content = repo.readme_content || ''
    return renderMarkdown(content, repo.repo_url)
  }, [repo.readme_content, repo.repo_url])

  // Handle image loading errors - fallback to master branch
  useEffect(() => {
    if (!contentRef.current) return

    const images = contentRef.current.querySelectorAll('img')
    
    const handleImageError = (event: Event) => {
      const img = event.target as HTMLImageElement
      const src = img.src
      
      // Only try once - if it's already tried master, don't retry
      if (src.includes('/master/') || img.dataset.retried === 'true') {
        return
      }
      
      // Try replacing /main/ with /master/
      if (src.includes('/main/')) {
        img.dataset.retried = 'true'
        img.src = src.replace('/main/', '/master/')
      }
    }

    images.forEach((img) => {
      img.addEventListener('error', handleImageError)
    })

    // Cleanup
    return () => {
      images.forEach((img) => {
        img.removeEventListener('error', handleImageError)
      })
    }
  }, [renderedReadme])

  return (
    <AnimatePresence>
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ 
          height: 'auto', 
          opacity: 1,
          transition: { duration: 0.3, ease: 'easeInOut' }
        }}
        exit={{ 
          height: 0, 
          opacity: 0,
          transition: { duration: 0.2, ease: 'easeIn' }
        }}
        className="w-full overflow-hidden"
      >
        <div className="readme-panel-container mx-4 sm:mx-8 mb-6">
          <div className="readme-panel-content">
            {/* Header */}
            <div className="flex items-start justify-between mb-4 pb-4 border-b border-zinc-700">
              <div className="flex-1 min-w-0">
                <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">
                  {repo.repo_full_name}
                </h3>
                <p className="text-sm text-zinc-400">
                  {repo.description || 'No description available'}
                </p>
              </div>
              <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                <div className="flex items-center gap-2 text-sm text-white">
                  <svg className="w-4 h-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  <span className="whitespace-nowrap">{repo.stars.toLocaleString()}</span>
                </div>
                <a
                  href={repo.repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 text-white hover:text-purple-400 transition-colors text-sm font-medium whitespace-nowrap flex items-center gap-1.5"
                >
                  GitHub
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
                <button
                  onClick={onClose}
                  className="text-white hover:text-purple-400 transition-colors p-1.5"
                  aria-label="Close README"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* README Content - Full Width */}
            <div className="readme-panel-body" ref={contentRef}>
              {repo.readme_content ? (
                <div 
                  className="prose prose-invert prose-sm sm:prose-base w-full"
                  style={{ maxWidth: '100%' }}
                  dangerouslySetInnerHTML={{ __html: renderedReadme }}
                />
              ) : (
                <p className="text-zinc-500 text-center py-8">No README available for this repository</p>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}

