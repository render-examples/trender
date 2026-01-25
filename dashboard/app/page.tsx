import { Suspense } from 'react'
import { getTopReposByLanguage, getTopRepos } from '@/lib/db'
import ScrollableRow from '@/components/ScrollableRow'
import LoadingSkeleton from '@/components/LoadingSkeleton'
import TypingTagline from '@/components/TypingTagline'

export const dynamic = 'force-dynamic'

async function RenderRow() {
  const repos = await getTopRepos(25, undefined, true)
  return <ScrollableRow title="Render" repos={repos} icon="/images/render_logomark.png" />
}

async function PythonRow() {
  const repos = await getTopReposByLanguage('Python', 25)
  return <ScrollableRow title="Python" repos={repos} icon="/images/python.png" />
}

async function TypeScriptRow() {
  const repos = await getTopReposByLanguage('TypeScript', 25)
  return <ScrollableRow title="TypeScript" repos={repos} icon="/images/typescript.png" />
}

async function GoRow() {
  const repos = await getTopReposByLanguage('Go', 25)
  return <ScrollableRow title="Go" repos={repos} icon="/images/go.png" />
}

function RowSkeleton({ title }: { title: string }) {
  return (
    <div className="mb-8 sm:mb-12">
      <h2 className="text-xl sm:text-2xl font-bold text-white mb-4 sm:mb-6 px-4 sm:px-8">{title}</h2>
      <LoadingSkeleton count={10} />
    </div>
  )
}

export default async function Home() {
  return (
    <div className="space-y-8">
      <TypingTagline />
      
      <Suspense fallback={<RowSkeleton title="Render" />}>
        <RenderRow />
      </Suspense>
      
      <Suspense fallback={<RowSkeleton title="Python" />}>
        <PythonRow />
      </Suspense>

      <Suspense fallback={<RowSkeleton title="TypeScript" />}>
        <TypeScriptRow />
      </Suspense>

      <Suspense fallback={<RowSkeleton title="Go" />}>
        <GoRow />
      </Suspense>

    </div>
  )
}
