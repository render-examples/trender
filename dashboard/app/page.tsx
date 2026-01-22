import { Suspense } from 'react'
import { getTopReposByLanguage, getTopRepos } from '@/lib/db'
import ScrollableRow from '@/components/ScrollableRow'
import LoadingSkeleton from '@/components/LoadingSkeleton'

export const dynamic = 'force-dynamic'

async function RenderRow() {
  const repos = await getTopRepos(50, undefined, true)
  return <ScrollableRow title="Render Projects" repos={repos} />
}

async function PythonRow() {
  const repos = await getTopReposByLanguage('Python', 50)
  return <ScrollableRow title="Python" repos={repos} />
}

async function TypeScriptRow() {
  const repos = await getTopReposByLanguage('TypeScript', 50)
  return <ScrollableRow title="TypeScript" repos={repos} />
}

async function GoRow() {
  const repos = await getTopReposByLanguage('Go', 50)
  return <ScrollableRow title="Go" repos={repos} />
}

function RowSkeleton({ title }: { title: string }) {
  return (
    <div className="mb-12">
      <h2 className="text-2xl font-bold text-white mb-6 px-8">{title}</h2>
      <LoadingSkeleton count={10} />
    </div>
  )
}

export default async function Home() {
  return (
    <div className="space-y-8">
      
      <Suspense fallback={<RowSkeleton title="Render Projects" />}>
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
