import { X, MapPin, DoorOpen } from 'lucide-react'
import type { Hotel } from '../../types'
import { RoomCard } from './RoomCard'
import { PracticalInfoCard } from './PracticalInfoCard'

export function HotelDetail({ hotel, onClose }: { hotel: Hotel; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4 flex items-center justify-between rounded-t-2xl">
          <div>
            <h2 className="text-lg font-bold">{hotel.name}</h2>
            <div className="flex items-center gap-1 text-sm text-gray-500">
              <MapPin className="w-3.5 h-3.5" />
              {hotel.address}
            </div>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4">
          <div className="flex items-center gap-1 text-sm text-gray-600 mb-3">
            <DoorOpen className="w-4 h-4" />
            <span>{hotel.rooms.length} 会場</span>
            {hotel.totalRoomCount && <span className="text-gray-400">（公称 {hotel.totalRoomCount}）</span>}
          </div>

          <div className="space-y-2">
            {hotel.rooms.map(room => (
              <RoomCard key={room.id} hotel={hotel} room={room} />
            ))}
          </div>

          {hotel.practicalInfo && <PracticalInfoCard info={hotel.practicalInfo} />}
        </div>
      </div>
    </div>
  )
}
