import { useEffect, useState } from 'react'
import { Loader2, Map, List, BarChart3, SlidersHorizontal, X, SearchX } from 'lucide-react'
import { useVenueStore } from '../store/venueStore'
import { Header } from '../components/layout/Header'
import { SearchBar } from '../components/layout/SearchBar'
import { FilterPanel } from '../components/layout/FilterPanel'
import { HotelCard } from '../components/hotel/HotelCard'
import { VenueMap } from '../components/map/VenueMap'
import { ComparisonBar } from '../components/comparison/ComparisonBar'
import { ComparisonTable } from '../components/comparison/ComparisonTable'
import { BIDashboard } from '../components/bi/BIDashboard'

export function SearchPage() {
  const loading = useVenueStore(s => s.loading)
  const loadHotels = useVenueStore(s => s.loadHotels)
  const results = useVenueStore(s => s.results)
  const showComparison = useVenueStore(s => s.showComparison)
  const comparisonRooms = useVenueStore(s => s.comparisonRooms)
  const viewMode = useVenueStore(s => s.viewMode)
  const setViewMode = useVenueStore(s => s.setViewMode)
  const [filterOpen, setFilterOpen] = useState(false)

  useEffect(() => {
    loadHotels()
  }, [loadHotels])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">データを読み込み中...</span>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      <Header />
      <SearchBar />

      {/* Mobile: view mode toggle + filter button */}
      <div className="lg:hidden flex items-center gap-2 px-4 py-2 bg-white border-b border-gray-200">
        <button
          onClick={() => setFilterOpen(true)}
          className="flex items-center gap-1 px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          フィルタ
        </button>
        <div className="flex-1" />
        <div className="flex border border-gray-300 rounded-lg overflow-hidden">
          <button
            onClick={() => setViewMode('list')}
            className={`px-3 py-1.5 text-xs flex items-center gap-1 ${viewMode === 'list' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600'}`}
          >
            <List className="w-3.5 h-3.5" />
            一覧
          </button>
          <button
            onClick={() => setViewMode('map')}
            className={`px-3 py-1.5 text-xs flex items-center gap-1 ${viewMode === 'map' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600'}`}
          >
            <Map className="w-3.5 h-3.5" />
            地図
          </button>
          <button
            onClick={() => setViewMode('bi')}
            className={`px-3 py-1.5 text-xs flex items-center gap-1 ${viewMode === 'bi' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600'}`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            分析
          </button>
        </div>
      </div>

      {/* Mobile filter drawer */}
      {filterOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={() => setFilterOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-72 bg-white shadow-xl">
            <div className="flex items-center justify-between p-3 border-b border-gray-200">
              <span className="font-semibold text-sm">フィルタ</span>
              <button onClick={() => setFilterOpen(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-4 h-4" />
              </button>
            </div>
            <FilterPanel />
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Desktop filter sidebar */}
        <FilterPanel className="hidden lg:block w-60 shrink-0" />

        {viewMode === 'bi' ? (
          /* BI Dashboard */
          <div className="flex-1 overflow-y-auto bg-gray-50">
            <BIDashboard />
          </div>
        ) : (
          <>
            {/* List */}
            <div className={`flex-1 overflow-y-auto ${viewMode === 'map' ? 'hidden lg:block' : ''}`}>
              <div className="p-4 space-y-3" style={{ paddingBottom: comparisonRooms.length > 0 ? '80px' : '16px' }}>
                {results.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                    <SearchX className="w-12 h-12 mb-3" />
                    <p className="text-sm">条件に一致する会場が見つかりません</p>
                    <p className="text-xs mt-1">フィルタ条件を変更してお試しください</p>
                  </div>
                ) : (
                  results.map(({ hotel, matchedRooms }) => (
                    <HotelCard key={hotel.id} hotel={hotel} matchedRooms={matchedRooms} />
                  ))
                )}
              </div>
            </div>

            {/* Map */}
            <div className={`lg:w-[45%] lg:shrink-0 ${viewMode === 'list' ? 'hidden lg:block' : 'flex-1'}`}>
              <VenueMap className="h-full" />
            </div>
          </>
        )}
      </div>

      <ComparisonBar />
      {showComparison && <ComparisonTable />}
    </div>
  )
}
