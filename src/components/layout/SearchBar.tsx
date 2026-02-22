import { useRef, useEffect } from 'react'
import { Search, X } from 'lucide-react'
import { useVenueStore } from '../../store/venueStore'

export function SearchBar() {
  const keyword = useVenueStore(s => s.filter.keyword)
  const setKeyword = useVenueStore(s => s.setKeyword)
  const resultCount = useVenueStore(s => s.results.length)
  const roomCount = useVenueStore(s => s.results.reduce((sum, r) => sum + r.matchedRooms.length, 0))
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [])

  const handleChange = (value: string) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setKeyword(value), 200)
  }

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-white border-b border-gray-200">
      <div className="relative flex-1 max-w-xl">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          ref={inputRef}
          type="text"
          placeholder="ホテル名・会場名・住所・設備で検索..."
          defaultValue={keyword}
          onChange={e => handleChange(e.target.value)}
          className="w-full pl-10 pr-8 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {keyword && (
          <button
            onClick={() => {
              setKeyword('')
              if (inputRef.current) inputRef.current.value = ''
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      <span className="text-sm text-gray-500 whitespace-nowrap">
        {resultCount}ホテル / {roomCount}会場
      </span>
    </div>
  )
}
