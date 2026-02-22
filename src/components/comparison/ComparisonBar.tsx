import { X, BarChart3 } from 'lucide-react'
import { useVenueStore } from '../../store/venueStore'

export function ComparisonBar() {
  const comparisonRooms = useVenueStore(s => s.comparisonRooms)
  const clearComparison = useVenueStore(s => s.clearComparison)
  const setShowComparison = useVenueStore(s => s.setShowComparison)
  const toggleComparison = useVenueStore(s => s.toggleComparisonRoom)

  if (comparisonRooms.length === 0) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-300 shadow-lg px-4 py-3">
      <div className="max-w-[1800px] mx-auto flex items-center gap-3">
        <span className="text-sm font-medium text-gray-700 shrink-0">
          比較: {comparisonRooms.length}件
        </span>
        <div className="flex-1 flex items-center gap-2 overflow-x-auto">
          {comparisonRooms.map(({ hotel, room }) => (
            <span
              key={`${hotel.id}:${room.id}`}
              className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full whitespace-nowrap"
            >
              {hotel.name} / {room.name}
              <button
                onClick={() => toggleComparison(hotel, room)}
                className="hover:text-blue-900"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={clearComparison}
            className="px-3 py-1.5 text-xs text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            クリア
          </button>
          <button
            onClick={() => setShowComparison(true)}
            className="px-3 py-1.5 text-xs text-white bg-blue-600 rounded-lg hover:bg-blue-700 flex items-center gap-1"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            比較する
          </button>
        </div>
      </div>
    </div>
  )
}
