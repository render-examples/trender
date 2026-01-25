'use client'

import './TypingTagline.css'

export default function TypingTagline() {
  return (
    <div className="typing-tagline-container">
      <p className="typing-tagline">
        <span className="typing-text">
          Discover the most-loved projects in your favorite languages. Powered by{' '}
          <a 
            href="https://render.com/docs/workflows" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-zinc-400 hover:text-white underline transition-colors"
          >
            Render Workflows
          </a>
        </span>
      </p>
    </div>
  )
}

