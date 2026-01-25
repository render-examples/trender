'use client'

import { useState, useEffect } from 'react'
import { Repository } from '@/lib/db'
import ScrollableRow from './ScrollableRow'

interface HomeClientProps {
  renderRepos: Repository[]
  pythonRepos: Repository[]
  typeScriptRepos: Repository[]
  goRepos: Repository[]
}

export default function HomeClient({ 
  renderRepos, 
  pythonRepos, 
  typeScriptRepos, 
  goRepos 
}: HomeClientProps) {
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null)
  const [selectedSection, setSelectedSection] = useState<string | null>(null)

  // Handle card click - close any open card, then open the selected one
  const handleCardClick = (repo: Repository, section: string) => {
    if (selectedRepo?.repo_full_name === repo.repo_full_name && selectedSection === section) {
      // Clicking the same card closes it
      setSelectedRepo(null)
      setSelectedSection(null)
    } else {
      // Close any open card and select new one
      setSelectedRepo(repo)
      setSelectedSection(section)
    }
  }

  // Close panel
  const handleClosePanel = () => {
    setSelectedRepo(null)
    setSelectedSection(null)
  }

  // Handle ESC key to close panel
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && selectedRepo) {
        handleClosePanel()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedRepo])

  return (
    <div className="space-y-8">
      <ScrollableRow 
        title="Render" 
        repos={renderRepos} 
        icon="/images/render_logomark.png"
        selectedRepo={selectedSection === 'render' ? selectedRepo : null}
        onCardClick={(repo) => handleCardClick(repo, 'render')}
        onClosePanel={handleClosePanel}
      />
      
      <ScrollableRow 
        title="Python" 
        repos={pythonRepos} 
        icon="/images/python.png"
        selectedRepo={selectedSection === 'python' ? selectedRepo : null}
        onCardClick={(repo) => handleCardClick(repo, 'python')}
        onClosePanel={handleClosePanel}
      />

      <ScrollableRow 
        title="TypeScript" 
        repos={typeScriptRepos} 
        icon="/images/typescript.png"
        selectedRepo={selectedSection === 'typescript' ? selectedRepo : null}
        onCardClick={(repo) => handleCardClick(repo, 'typescript')}
        onClosePanel={handleClosePanel}
      />

      <ScrollableRow 
        title="Go" 
        repos={goRepos} 
        icon="/images/go.png"
        selectedRepo={selectedSection === 'go' ? selectedRepo : null}
        onCardClick={(repo) => handleCardClick(repo, 'go')}
        onClosePanel={handleClosePanel}
      />
    </div>
  )
}

