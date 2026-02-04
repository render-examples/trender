'use client'

import { useState, useEffect } from 'react'
import { Repository } from '@/lib/db'
import ScrollableRow from '@/components/ScrollableRow'

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
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  // Handle card click - close any open card, then open the selected one
  const handleCardClick = (repo: Repository, section: string, index: number) => {
    if (selectedRepo?.repo_full_name === repo.repo_full_name && selectedSection === section && selectedIndex === index) {
      // Clicking the same card closes it
      setSelectedRepo(null)
      setSelectedSection(null)
      setSelectedIndex(null)
    } else {
      // Close any open card and select new one
      setSelectedRepo(repo)
      setSelectedSection(section)
      setSelectedIndex(index)
    }
  }

  // Close panel
  const handleClosePanel = () => {
    setSelectedRepo(null)
    setSelectedSection(null)
    setSelectedIndex(null)
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
        title="RENDER" 
        repos={renderRepos} 
        icon="/images/render-logomark.png"
        selectedRepo={selectedSection === 'render' ? selectedRepo : null}
        selectedIndex={selectedSection === 'render' ? selectedIndex : null}
        onCardClick={(repo, index) => handleCardClick(repo, 'render', index)}
        onClosePanel={handleClosePanel}
      />
      
      <ScrollableRow 
        title="PYTHON" 
        repos={pythonRepos} 
        icon="/images/python.png"
        selectedRepo={selectedSection === 'python' ? selectedRepo : null}
        selectedIndex={selectedSection === 'python' ? selectedIndex : null}
        onCardClick={(repo, index) => handleCardClick(repo, 'python', index)}
        onClosePanel={handleClosePanel}
      />

      <ScrollableRow 
        title="TYPESCRIPT" 
        repos={typeScriptRepos} 
        icon="/images/typescript.png"
        selectedRepo={selectedSection === 'typescript' ? selectedRepo : null}
        selectedIndex={selectedSection === 'typescript' ? selectedIndex : null}
        onCardClick={(repo, index) => handleCardClick(repo, 'typescript', index)}
        onClosePanel={handleClosePanel}
      />

      <ScrollableRow 
        title="GO" 
        repos={goRepos} 
        icon="/images/go.png"
        selectedRepo={selectedSection === 'go' ? selectedRepo : null}
        selectedIndex={selectedSection === 'go' ? selectedIndex : null}
        onCardClick={(repo, index) => handleCardClick(repo, 'go', index)}
        onClosePanel={handleClosePanel}
      />
    </div>
  )
}

