import { Maximize2, ArrowUpDown, Users, Layers, BarChart3 } from 'lucide-react'
import type { Hotel, Room } from '../../types'
import { formatArea, formatCeiling, formatCapacity, capacityTypeLabel } from '../../utils/format'
import { useVenueStore } from '../../store/venueStore'

export function RoomCard({ hotel, room }: { hotel: Hotel; room: Room }) {
  const comparisonRooms = useVenueStore(s => s.comparisonRooms)
  const toggleComparison = useVenueStore(s => s.toggleComparisonRoom)

  const isSelected = comparisonRooms.some(c => c.hotel.id === hotel.id && c.room.id === room.id)
  const canAdd = comparisonRooms.length < 6

  const cap = room.capacity
  const capacityEntries = (Object.entries(cap) as [string, number | undefined][])
    .filter(([, v]) => v != null && v > 0)

  return (
    <div className="border border-gray-200 rounded-lg p-3 bg-gray-50 hover:bg-gray-100 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-gray-900 truncate">{room.name}</h4>
            {room.floor && <span className="text-xs text-gray-500 shrink-0">{room.floor}</span>}
            {room.usageCount != null && room.usageCount > 0 && (
              <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-emerald-50 text-emerald-600 shrink-0">
                <BarChart3 className="w-2.5 h-2.5" />
                {room.usageCount}件
                {room.typicalSeatCount != null && ` / ${room.typicalSeatCount}席`}
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-xs text-gray-600">
            {room.areaSqm != null && (
              <span className="flex items-center gap-1">
                <Maximize2 className="w-3 h-3" />
                {formatArea(room.areaSqm)}
              </span>
            )}
            {room.ceilingHeightM != null && (
              <span className="flex items-center gap-1">
                <ArrowUpDown className="w-3 h-3" />
                天井 {formatCeiling(room.ceilingHeightM)}
              </span>
            )}
            {room.divisions.length > 0 && (
              <span className="flex items-center gap-1">
                <Layers className="w-3 h-3" />
                {room.divisions.length}分割可
              </span>
            )}
          </div>

          {capacityEntries.length > 0 && (
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5 text-xs">
              <Users className="w-3 h-3 text-gray-400 mt-0.5" />
              {capacityEntries.map(([key, val]) => (
                <span key={key} className="text-gray-600">
                  <span className="text-gray-400">{capacityTypeLabel[key] ?? key}:</span> {formatCapacity(val!)}
                </span>
              ))}
            </div>
          )}

          {room.equipment && (
            <p className="text-xs text-gray-500 mt-1 line-clamp-1">{room.equipment}</p>
          )}
        </div>

        <label className="flex items-center gap-1 shrink-0 cursor-pointer">
          <input
            type="checkbox"
            checked={isSelected}
            disabled={!isSelected && !canAdd}
            onChange={() => toggleComparison(hotel, room)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-xs text-gray-500">比較</span>
        </label>
      </div>
    </div>
  )
}
