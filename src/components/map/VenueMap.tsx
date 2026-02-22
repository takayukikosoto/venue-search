import { useEffect, useRef, useMemo } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useVenueStore } from '../../store/venueStore'
import { HotelMarker } from './HotelMarker'
import type { FilteredResult } from '../../utils/search'

function FitBounds({ results }: { results: FilteredResult[] }) {
  const map = useMap()
  const prevBoundsRef = useRef<string>('')

  useEffect(() => {
    const points = results
      .filter(r => r.hotel.lat != null && r.hotel.lng != null)
      .map(r => [r.hotel.lat!, r.hotel.lng!] as [number, number])

    if (points.length === 0) return

    const boundsKey = points.map(p => `${p[0]},${p[1]}`).join('|')
    if (boundsKey === prevBoundsRef.current) return
    prevBoundsRef.current = boundsKey

    const bounds = L.latLngBounds(points)
    const isMobile = window.innerWidth < 768
    map.fitBounds(bounds, {
      padding: isMobile ? [20, 20] : [40, 40],
      maxZoom: 14,
    })
  }, [results, map])

  return null
}

function MapResizeHandler() {
  const map = useMap()
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize())
    observer.observe(map.getContainer())
    return () => observer.disconnect()
  }, [map])
  return null
}

export function VenueMap({ className = '' }: { className?: string }) {
  const results = useVenueStore(s => s.results)
  const selectedHotelId = useVenueStore(s => s.selectedHotelId)

  const markers = useMemo(() =>
    results.map(({ hotel, matchedRooms }) => (
      <HotelMarker
        key={hotel.id}
        hotel={hotel}
        matchedRooms={matchedRooms}
        isHighlighted={hotel.id === selectedHotelId}
      />
    )),
    [results, selectedHotelId],
  )

  return (
    <div className={`${className}`}>
      <MapContainer
        center={[35.68, 139.76]}
        zoom={11}
        className="w-full h-full rounded-lg"
        bounceAtZoomLimits={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          updateWhenZooming={false}
          updateWhenIdle={true}
        />
        <FitBounds results={results} />
        <MapResizeHandler />
        {markers}
      </MapContainer>
    </div>
  )
}
