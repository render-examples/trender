import { getTopReposByLanguage, getTopRepos } from '@/lib/db'
import TypingTagline from '@/components/TypingTagline'
import HomeClient from '@/components/HomeClient'

export const dynamic = 'force-dynamic'

export default async function Home() {
  // Fetch all repos in parallel
  const [renderRepos, pythonRepos, typeScriptRepos, goRepos] = await Promise.all([
    getTopRepos(25, undefined, true),
    getTopReposByLanguage('Python', 25),
    getTopReposByLanguage('TypeScript', 25),
    getTopReposByLanguage('Go', 25),
  ])

  return (
    <div className="space-y-8">
      <TypingTagline />
      <HomeClient 
        renderRepos={renderRepos}
        pythonRepos={pythonRepos}
        typeScriptRepos={typeScriptRepos}
        goRepos={goRepos}
      />
    </div>
  )
}
