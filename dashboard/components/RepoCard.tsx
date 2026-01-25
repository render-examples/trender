'use client'

import { motion } from 'framer-motion'
import { Repository } from '@/lib/db'
import { formatStarCount } from '@/lib/formatters'

interface RepoCardProps {
  repo: Repository
  isSelected: boolean
  onCardClick: () => void
}

export default function RepoCard({ repo, isSelected, onCardClick }: RepoCardProps) {
  return (
    <motion.div
      className="flex-shrink-0 cursor-pointer"
      onClick={onCardClick}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ opacity: { duration: 0.2 } }}
    >
      <div
        className={`repo-card-collapsed bg-black border transition-all duration-300 flex flex-col relative group ${
          isSelected 
            ? 'border-purple-500 shadow-lg shadow-purple-500/50' 
            : 'border-zinc-700 hover:border-purple-500'
        }`}
        style={{ 
          height: '280px'
        }}
      >
        <div className="flex flex-col p-4 sm:p-6 h-full">
          <div className="flex items-start justify-between mb-2 sm:mb-3 flex-shrink-0">
            <h3 
              className="text-base sm:text-lg font-semibold text-white truncate pr-2"
            >
              {repo.repo_full_name}
            </h3>
            <span className="text-yellow-400 flex items-center gap-1 flex-shrink-0 text-sm sm:text-base">
              <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              {formatStarCount(repo.stars)}
            </span>
          </div>

          <p 
            className="text-xs sm:text-sm text-zinc-400 flex-1 line-clamp-4"
          >
            {repo.description || 'No description available'}
          </p>

          {/* Visual indicator that card is clickable with rotation animation */}
          <div className={`absolute inset-0 pointer-events-none transition-opacity duration-300 ${
            isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
          }`}>
            <div className="absolute bottom-2 right-2 text-purple-400">
              <svg 
                className={`w-5 h-5 transition-transform duration-300 ${
                  isSelected ? 'rotate-0' : '-rotate-90'
                }`}
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
