import { create } from 'zustand'
import type { Hotel, Room, FilterState, Region, CapacityType, UsageRecord } from '../types'
import { filterHotels, type FilteredResult } from '../utils/search'
import { supabase } from '../lib/supabase'

interface VenueState {
  hotels: Hotel[]
  usageRecords: UsageRecord[]
  loading: boolean
  filter: FilterState
  results: FilteredResult[]
  selectedHotelId: string | null
  comparisonRooms: { hotel: Hotel; room: Room }[]
  showComparison: boolean
  viewMode: 'list' | 'map' | 'bi'

  loadHotels: () => Promise<void>
  setKeyword: (keyword: string) => void
  toggleRegion: (region: Region) => void
  setAreaMin: (v: number | undefined) => void
  setAreaMax: (v: number | undefined) => void
  setCeilingMin: (v: number | undefined) => void
  setCeilingMax: (v: number | undefined) => void
  setCapacityMin: (v: number | undefined) => void
  setCapacityMax: (v: number | undefined) => void
  setCapacityType: (type: CapacityType) => void
  setHasDivisions: (v: boolean | null) => void
  setHasUsageRecords: (v: boolean | null) => void
  resetFilters: () => void
  selectHotel: (id: string | null) => void
  toggleComparisonRoom: (hotel: Hotel, room: Room) => void
  clearComparison: () => void
  setShowComparison: (show: boolean) => void
  setViewMode: (mode: 'list' | 'map' | 'bi') => void
  getUsageForHotel: (hotelId: string) => UsageRecord[]
  getUsageForRoom: (roomId: string) => UsageRecord[]
}

const defaultFilter: FilterState = {
  keyword: '',
  regions: [],
  areaMin: undefined,
  areaMax: undefined,
  ceilingMin: undefined,
  ceilingMax: undefined,
  capacityMin: undefined,
  capacityMax: undefined,
  capacityType: 'theater',
  hasDivisions: null,
  hasUsageRecords: null,
}

function applyFilter(hotels: Hotel[], filter: FilterState): FilteredResult[] {
  return filterHotels(hotels, filter)
}

export const useVenueStore = create<VenueState>((set, get) => ({
  hotels: [],
  usageRecords: [],
  loading: true,
  filter: { ...defaultFilter },
  results: [],
  selectedHotelId: null,
  comparisonRooms: [],
  showComparison: false,
  viewMode: 'list',

  loadHotels: async () => {
    set({ loading: true })
    const [venuesResult, usageResult] = await Promise.all([
      supabase.from('venues').select('*, rooms(*)').order('name'),
      supabase.from('usage_records').select('*').order('date', { ascending: false, nullsFirst: false }),
    ])
    if (venuesResult.error) throw venuesResult.error
    if (usageResult.error) throw usageResult.error

    const hotels: Hotel[] = venuesResult.data.map((v: Record<string, unknown>) => ({
      id: v.id,
      name: v.name,
      address: v.address,
      region: v.region,
      lat: v.lat,
      lng: v.lng,
      usageCount: v.usage_count,
      totalRoomCount: v.total_room_count,
      practicalInfo: v.practical_info as Hotel['practicalInfo'],
      rooms: ((v.rooms as Record<string, unknown>[]) ?? []).map((r) => ({
        id: r.id,
        name: r.name,
        floor: r.floor,
        areaSqm: r.area_sqm,
        ceilingHeightM: r.ceiling_height_m,
        capacity: {
          theater: r.capacity_theater,
          school: r.capacity_school,
          banquet: r.capacity_banquet,
          standing: r.capacity_standing,
        },
        divisions: r.divisions as Room['divisions'],
        equipment: (r.extra as Record<string, unknown>)?.equipment as string | undefined,
        features: (r.extra as Record<string, unknown>)?.features as string | undefined,
        loadingDock: (r.extra as Record<string, unknown>)?.loadingDock as string | undefined,
        usageCount: r.usage_count,
        typicalSeatCount: (r.extra as Record<string, unknown>)?.typicalSeatCount != null
          ? Number((r.extra as Record<string, unknown>).typicalSeatCount) : undefined,
        typicalUse: (r.extra as Record<string, unknown>)?.typicalUse as string | undefined,
      })) as Room[],
    }))

    const usageRecords: UsageRecord[] = usageResult.data.map((u: Record<string, unknown>) => {
      const details = (u.details ?? {}) as Record<string, unknown>
      return {
        id: u.id as string,
        hotelName: u.hotel_name as string,
        hotelId: u.venue_id as string | undefined,
        roomName: u.room_name as string,
        roomId: u.room_id as string | undefined,
        seminarName: u.seminar_name as string,
        date: u.date as string | undefined,
        year: u.year as number | undefined,
        sourceFile: u.source_file as string,
        floor: details.floor as string | undefined,
        seatCount: details.seatCount != null ? Number(details.seatCount) : undefined,
        areaSqm: details.areaSqm != null ? Number(details.areaSqm) : undefined,
        ceilingHeightM: details.ceilingHeightM != null ? Number(details.ceilingHeightM) : undefined,
        attendeeEstimate: details.attendeeEstimate != null ? Number(details.attendeeEstimate) : undefined,
        usageHours: details.usageHours as string | undefined,
        greenRooms: u.green_rooms as UsageRecord['greenRooms'],
        equipment: u.equipment as string[] | undefined,
      }
    })

    const results = applyFilter(hotels, get().filter)
    set({ hotels, usageRecords, results, loading: false })
  },

  setKeyword: (keyword) => {
    const filter = { ...get().filter, keyword }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },

  toggleRegion: (region) => {
    const current = get().filter.regions
    const regions = current.includes(region)
      ? current.filter(r => r !== region)
      : [...current, region]
    const filter = { ...get().filter, regions }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },

  setAreaMin: (v) => {
    const filter = { ...get().filter, areaMin: v }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },
  setAreaMax: (v) => {
    const filter = { ...get().filter, areaMax: v }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },
  setCeilingMin: (v) => {
    const filter = { ...get().filter, ceilingMin: v }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },
  setCeilingMax: (v) => {
    const filter = { ...get().filter, ceilingMax: v }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },
  setCapacityMin: (v) => {
    const filter = { ...get().filter, capacityMin: v }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },
  setCapacityMax: (v) => {
    const filter = { ...get().filter, capacityMax: v }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },
  setCapacityType: (type) => {
    const filter = { ...get().filter, capacityType: type }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },
  setHasDivisions: (v) => {
    const filter = { ...get().filter, hasDivisions: v }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },
  setHasUsageRecords: (v) => {
    const filter = { ...get().filter, hasUsageRecords: v }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },

  resetFilters: () => {
    const filter = { ...defaultFilter }
    set({ filter, results: applyFilter(get().hotels, filter) })
  },

  selectHotel: (id) => set({ selectedHotelId: id }),

  toggleComparisonRoom: (hotel, room) => {
    const current = get().comparisonRooms
    const key = `${hotel.id}:${room.id}`
    const exists = current.some(c => `${c.hotel.id}:${c.room.id}` === key)
    if (exists) {
      set({ comparisonRooms: current.filter(c => `${c.hotel.id}:${c.room.id}` !== key) })
    } else if (current.length < 6) {
      set({ comparisonRooms: [...current, { hotel, room }] })
    }
  },

  clearComparison: () => set({ comparisonRooms: [], showComparison: false }),
  setShowComparison: (show) => set({ showComparison: show }),
  setViewMode: (mode) => set({ viewMode: mode }),

  getUsageForHotel: (hotelId) => {
    return get().usageRecords.filter(r => r.hotelId === hotelId)
  },
  getUsageForRoom: (roomId) => {
    return get().usageRecords.filter(r => r.roomId === roomId)
  },
}))
