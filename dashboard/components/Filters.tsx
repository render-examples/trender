'use client'

import { useRouter } from 'next/navigation'

interface FiltersProps {
  selectedLanguage?: string
  renderOnly: boolean
}

export default function Filters({ selectedLanguage, renderOnly }: FiltersProps) {
  const router = useRouter()

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const lang = e.target.value === 'all' ? '' : e.target.value
    const params = new URLSearchParams()
    if (lang) params.set('language', lang)
    if (renderOnly) params.set('render', 'true')
    router.push(`/?${params.toString()}`)
  }

  const handleRenderOnlyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const checked = e.target.checked
    const params = new URLSearchParams()
    if (selectedLanguage) params.set('language', selectedLanguage)
    if (checked) params.set('render', 'true')
    router.push(`/?${params.toString()}`)
  }

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <div className="flex flex-wrap gap-4 items-center">
        <div>
          <label className="text-sm font-medium text-gray-700 mr-2">
            Language:
          </label>
          <select
            className="border border-gray-300 rounded px-3 py-1"
            value={selectedLanguage || 'all'}
            onChange={handleLanguageChange}
          >
            <option value="all">All Languages</option>
            <option value="Python">Python</option>
            <option value="TypeScript">TypeScript</option>
            <option value="Go">Go</option>
          </select>
        </div>
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={renderOnly}
            onChange={handleRenderOnlyChange}
            className="mr-2"
          />
          <span className="text-sm font-medium text-gray-700">
            Show only Render projects
          </span>
        </label>
      </div>
    </div>
  )
}

