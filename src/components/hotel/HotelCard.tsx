import { useState } from 'react'
import { MapPin, ChevronDown, ChevronUp, DoorOpen, BarChart3 } from 'lucide-react'
import type { Hotel, Room } from '../../types'
import { RoomCard } from './RoomCard'
import { PracticalInfoCard } from './PracticalInfoCard'
import { UsageHistoryPanel } from './UsageHistoryPanel'
import { useVenueStore } from '../../store/venueStore'

const regionColors: Record<string, string> = {
  '東京': 'bg-blue-100 text-blue-700',
  '大阪': 'bg-orange-100 text-orange-700',
  '名古屋': 'bg-green-100 text-green-700',
  '福岡': 'bg-purple-100 text-purple-700',
  '京都': 'bg-red-100 text-red-700',
}

export function HotelCard({ hotel, matchedRooms }: { hotel: Hotel; matchedRooms: Room[] }) {
  const [expanded, setExpanded] = useState(false)
  const selectHotel = useVenueStore(s => s.selectHotel)
  const selectedHotelId = useVenueStore(s => s.selectedHotelId)
  const getUsageForHotel = useVenueStore(s => s.getUsageForHotel)
  const isHighlighted = selectedHotelId === hotel.id
  const usageCount = hotel.usageCount ?? 0

  return (
    <div
      className={`bg-white rounded-xl border transition-all ${
        isHighlighted ? 'border-blue-400 ring-2 ring-blue-100' : 'border-gray-200 hover:border-gray-300'
      }`}
      onMouseEnter={() => selectHotel(hotel.id)}
      onMouseLeave={() => selectHotel(null)}
    >
      <div className="p-4">
        {/* Hotel header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-bold text-gray-900">{hotel.name}</h3>
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${regionColors[hotel.region] || 'bg-gray-100 text-gray-600'}`}>
                {hotel.region}
              </span>
            </div>
            <div className="flex items-center gap-1 mt-1 text-xs text-gray-500">
              <MapPin className="w-3 h-3" />
              <span>{hotel.address}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {usageCount > 0 && (
              <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-emerald-50 text-emerald-700">
                <BarChart3 className="w-3 h-3" />
                実績{usageCount}件
              </span>
            )}
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <DoorOpen className="w-3.5 h-3.5" />
              <span>{matchedRooms.length}会場</span>
            </div>
          </div>
        </div>

        {/* Room list (first 3 always visible) */}
        <div className="mt-3 space-y-2">
          {(expanded ? matchedRooms : matchedRooms.slice(0, 2)).map(room => (
            <RoomCard key={room.id} hotel={hotel} room={room} />
          ))}
        </div>

        {matchedRooms.length > 2 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-2 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {expanded ? '折りたたむ' : `他 ${matchedRooms.length - 2} 会場を表示`}
          </button>
        )}

        {/* Practical info (expanded) */}
        {expanded && hotel.practicalInfo && (
          <PracticalInfoCard info={hotel.practicalInfo} />
        )}

        {/* Usage history (expanded) */}
        {expanded && usageCount > 0 && (
          <UsageHistoryPanel records={getUsageForHotel(hotel.id)} />
        )}
      </div>
    </div>
  )
}
