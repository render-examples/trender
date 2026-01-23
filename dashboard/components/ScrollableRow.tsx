'use client'

import { useRef } from 'react'
import { LayoutGroup } from 'framer-motion'
import { Repository } from '@/lib/db'
import RepoCard from './RepoCard'
import LoadingSkeleton from './LoadingSkeleton'

interface ScrollableRowProps {
  title: string
  repos: Repository[]
}

// Generate placeholder repos with lorem ipsum
// Uses deterministic values to avoid hydration mismatches
const generatePlaceholderRepos = (count: number, language: string): Repository[] => {
  const loremTexts = [
    'A modern framework for building scalable applications with best practices',
    'High-performance library for efficient data processing and analytics',
    'Elegant toolkit for creating beautiful user interfaces quickly',
    'Robust solution for enterprise-level distributed systems',
    'Lightweight utility collection for common development tasks',
    'Advanced framework for building real-time collaborative applications',
    'Comprehensive platform for deploying cloud-native microservices',
    'Innovative library for reactive programming patterns',
    'Powerful engine for processing large-scale data streams',
    'Developer-friendly tools for rapid application prototyping',
  ]
  
  // Use a fixed date to avoid hydration mismatches
  const fixedDate = new Date('2024-01-01T00:00:00Z')
  
  return Array.from({ length: count }).map((_, i) => ({
    id: -i - 1,
    repo_full_name: `placeholder/project-${i + 1}`,
    repo_url: '#',
    language,
    // Use deterministic star count based on index to avoid hydration mismatch
    stars: 1000 + (i * 100),
    star_velocity: 0,
    activity_score: 0,
    momentum_score: 0,
    commits_last_7_days: 0,
    issues_closed_last_7_days: 0,
    active_contributors: 0,
    description: loremTexts[i % loremTexts.length],
    readme_content: null,
    uses_render: false,
    render_category: null,
    render_services: [],
    has_blueprint_button: false,
    render_complexity_score: 0,
    created_at: fixedDate,
    last_updated: fixedDate,
  }))
}

export default function ScrollableRow({ title, repos }: ScrollableRowProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  
  // Fill with placeholders if we have fewer than 50 repos
  const displayRepos = repos.length > 0 
    ? [...repos, ...generatePlaceholderRepos(Math.max(0, 50 - repos.length), repos[0]?.language || title)]
    : generatePlaceholderRepos(50, title)

  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = 400
      const newScrollLeft = scrollContainerRef.current.scrollLeft + (direction === 'right' ? scrollAmount : -scrollAmount)
      scrollContainerRef.current.scrollTo({
        left: newScrollLeft,
        behavior: 'smooth'
      })
    }
  }

  return (
    <div className="mb-12 relative group">
      <div className="flex items-center gap-4 mb-6 px-8">
        <h2 className="text-2xl font-bold text-white">{title}</h2>
      </div>
      
      {/* Left scroll arrow */}
      <button
        onClick={() => scroll('left')}
        className="absolute left-0 top-1/2 -translate-y-1/2 z-20 bg-black/80 hover:bg-black/95 text-white p-3 rounded-r-lg opacity-0 group-hover:opacity-100 transition-opacity border border-zinc-800"
        aria-label="Scroll left"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Right scroll arrow */}
      <button
        onClick={() => scroll('right')}
        className="absolute right-0 top-1/2 -translate-y-1/2 z-20 bg-black/80 hover:bg-black/95 text-white p-3 rounded-l-lg opacity-0 group-hover:opacity-100 transition-opacity border border-zinc-800"
        aria-label="Scroll right"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      <div ref={scrollContainerRef} className="overflow-x-auto scrollbar-hide">
        <LayoutGroup>
          <div className="flex gap-4 px-8 pb-4">
            {displayRepos.length === 0 ? (
              <LoadingSkeleton count={10} />
            ) : (
              displayRepos.map((repo, index) => (
                <RepoCard key={`${repo.repo_full_name}-${index}`} repo={repo} />
              ))
            )}
          </div>
        </LayoutGroup>
      </div>
    </div>
  )
}
