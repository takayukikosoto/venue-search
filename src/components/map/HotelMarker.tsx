import { Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import type { Hotel, Room } from '../../types'
import { formatCapacity } from '../../utils/format'

const defaultIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const highlightIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [30, 49],
  iconAnchor: [15, 49],
  popupAnchor: [1, -40],
  shadowSize: [49, 49],
  className: 'highlighted-marker',
})

function getMaxCapacity(rooms: Room[]): number {
  return Math.max(0, ...rooms.map(r =>
    Math.max(
      r.capacity.theater ?? 0,
      r.capacity.school ?? 0,
      r.capacity.banquet ?? 0,
      r.capacity.standing ?? 0,
      r.capacity.max ?? 0,
    )
  ))
}

export function HotelMarker({ hotel, matchedRooms, isHighlighted }: {
  hotel: Hotel
  matchedRooms: Room[]
  isHighlighted: boolean
}) {
  if (hotel.lat == null || hotel.lng == null) return null

  const maxCap = getMaxCapacity(matchedRooms)

  return (
    <Marker
      position={[hotel.lat, hotel.lng]}
      icon={isHighlighted ? highlightIcon : defaultIcon}
      zIndexOffset={isHighlighted ? 1000 : 0}
    >
      <Popup
        maxWidth={260}
        minWidth={160}
        autoPanPadding={[20, 20] as L.PointExpression}
        keepInView={true}
        closeOnClick={false}
      >
        <div className="text-sm">
          <p className="font-bold text-gray-900">{hotel.name}</p>
          <p className="text-xs text-gray-500 mt-0.5">{hotel.region}</p>
          <p className="text-xs mt-1">会場数: {matchedRooms.length}</p>
          {maxCap > 0 && <p className="text-xs">最大収容: {formatCapacity(maxCap)}</p>}
        </div>
      </Popup>
    </Marker>
  )
}
