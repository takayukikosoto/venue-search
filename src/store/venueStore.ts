import { create } from 'zustand'
import type { Hotel, Room, FilterState, Region, CapacityType, UsageRecord } from '../types'
import { filterHotels, type FilteredResult } from '../utils/search'

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
    const [venuesRes, usageRes] = await Promise.all([
      fetch('/data/venues.json'),
      fetch('/data/usage-records.json'),
    ])
    const hotels: Hotel[] = await venuesRes.json()
    const usageRecords: UsageRecord[] = await usageRes.json()
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
