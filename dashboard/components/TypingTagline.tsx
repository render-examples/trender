'use client'

import './TypingTagline.css'
import WorkflowPanel from '@/components/WorkflowPanel'

export default function TypingTagline() {
  return (
    <div className="space-y-0">
      <div className="typing-tagline-container">
        <p className="typing-tagline">
          <span className="typing-text">
            Discover the most-loved projects in your favorite languages. Powered by{' '}
            <a 
              href="https://render.com/docs/workflows" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-purple-400 hover:text-purple-300 underline transition-colors"
            >
              Render Workflows
            </a>
          </span>
        </p>
      </div>
      <WorkflowPanel />
    </div>
  )
}

