import type { Hotel, Room, FilterState, Capacity, CapacityType } from '../types'

// 全角→半角変換
function toHalfWidth(str: string): string {
  return str.replace(/[Ａ-Ｚａ-ｚ０-９]/g, (s) =>
    String.fromCharCode(s.charCodeAt(0) - 0xFEE0)
  )
}

// カタカナ→ひらがな変換
function katakanaToHiragana(str: string): string {
  return str.replace(/[\u30A1-\u30F6]/g, (s) =>
    String.fromCharCode(s.charCodeAt(0) - 0x60)
  )
}

function normalize(str: string): string {
  return katakanaToHiragana(toHalfWidth(str)).toLowerCase()
}

function getCapacityValue(capacity: Capacity, type: CapacityType): number | undefined {
  const val = capacity[type]
  if (val != null) return val
  return capacity.max
}

function getMaxCapacity(room: Room, type: CapacityType): number {
  const main = getCapacityValue(room.capacity, type) ?? 0
  return main
}

function roomMatchesText(room: Room, terms: string[]): boolean {
  const text = normalize([room.name, room.floor, room.equipment, room.features].filter(Boolean).join(' '))
  return terms.every(t => text.includes(t))
}

function hotelMatchesText(hotel: Hotel, terms: string[]): boolean {
  const hotelText = normalize(
    [hotel.name, hotel.address, hotel.practicalInfo?.nearestStation].filter(Boolean).join(' ')
  )
  if (terms.every(t => hotelText.includes(t))) return true
  return hotel.rooms.some(r => roomMatchesText(r, terms))
}

export interface FilteredResult {
  hotel: Hotel
  matchedRooms: Room[]
}

export function filterHotels(hotels: Hotel[], filter: FilterState): FilteredResult[] {
  const results: FilteredResult[] = []

  const terms = filter.keyword
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map(normalize)

  for (const hotel of hotels) {
    // Region filter
    if (filter.regions.length > 0 && !filter.regions.includes(hotel.region)) continue

    // Usage records filter
    if (filter.hasUsageRecords === true && (!hotel.usageCount || hotel.usageCount === 0)) continue

    // Keyword filter on hotel level
    if (terms.length > 0 && !hotelMatchesText(hotel, terms)) continue

    // Room-level filters
    let matchedRooms = hotel.rooms

    if (filter.areaMin != null || filter.areaMax != null || filter.ceilingMin != null || filter.ceilingMax != null || filter.capacityMin != null || filter.capacityMax != null || filter.hasDivisions != null) {
      matchedRooms = hotel.rooms.filter(room => {
        if (filter.areaMin != null && (room.areaSqm == null || room.areaSqm < filter.areaMin)) return false
        if (filter.areaMax != null && (room.areaSqm == null || room.areaSqm > filter.areaMax)) return false
        if (filter.ceilingMin != null && (room.ceilingHeightM == null || room.ceilingHeightM < filter.ceilingMin)) return false
        if (filter.ceilingMax != null && (room.ceilingHeightM == null || room.ceilingHeightM > filter.ceilingMax)) return false

        if (filter.capacityMin != null || filter.capacityMax != null) {
          const cap = getMaxCapacity(room, filter.capacityType)
          if (cap === 0) return false
          if (filter.capacityMin != null && cap < filter.capacityMin) return false
          if (filter.capacityMax != null && cap > filter.capacityMax) return false
        }

        if (filter.hasDivisions === true && room.divisions.length === 0) return false
        if (filter.hasDivisions === false && room.divisions.length > 0) return false

        return true
      })
    }

    // If keyword was targeting rooms, narrow down
    if (terms.length > 0) {
      const hotelText = normalize([hotel.name, hotel.address, hotel.practicalInfo?.nearestStation].filter(Boolean).join(' '))
      const hotelMatchesDirectly = terms.every(t => hotelText.includes(t))
      if (!hotelMatchesDirectly) {
        matchedRooms = matchedRooms.filter(r => roomMatchesText(r, terms))
      }
    }

    if (matchedRooms.length > 0) {
      results.push({ hotel, matchedRooms })
    }
  }

  return results
}
