import { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, ScatterChart, Scatter, Cell, Legend,
} from 'recharts'
import { Building2, DoorOpen, FileText, MapPin } from 'lucide-react'
import { useVenueStore } from '../../store/venueStore'
import type { Region } from '../../types'

const REGION_COLORS: Record<string, string> = {
  '東京': '#3b82f6',
  '大阪': '#ef4444',
  '名古屋': '#f59e0b',
  '福岡': '#10b981',
  '京都': '#8b5cf6',
  '横浜': '#06b6d4',
  '神戸': '#ec4899',
  '札幌': '#6366f1',
  '仙台': '#14b8a6',
  '千葉': '#f97316',
}

function KpiCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: number | string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
      <div className="p-2 bg-blue-50 rounded-lg">
        <Icon className="w-5 h-5 text-blue-600" />
      </div>
      <div>
        <div className="text-2xl font-bold text-gray-900">{value}</div>
        <div className="text-xs text-gray-500">{label}</div>
      </div>
    </div>
  )
}

export function BIDashboard() {
  const results = useVenueStore(s => s.results)
  const usageRecords = useVenueStore(s => s.usageRecords)
  const hotels = useVenueStore(s => s.hotels)

  // フィルタ済み施設IDセット
  const filteredHotelIds = useMemo(
    () => new Set(results.map(r => r.hotel.id)),
    [results],
  )

  // フィルタ済み利用実績
  const filteredUsage = useMemo(
    () => usageRecords.filter(r => r.hotelId && filteredHotelIds.has(r.hotelId)),
    [usageRecords, filteredHotelIds],
  )

  // --- KPI ---
  const kpi = useMemo(() => {
    const totalRooms = results.reduce((sum, r) => sum + r.hotel.rooms.length, 0)
    const regions = new Set(results.map(r => r.hotel.region))
    return {
      venues: results.length,
      rooms: totalRooms,
      usages: filteredUsage.length,
      regions: regions.size,
    }
  }, [results, filteredUsage])

  // --- 地域別利用件数 ---
  const regionUsageData = useMemo(() => {
    const hotelRegionMap = new Map<string, Region>()
    for (const h of hotels) {
      hotelRegionMap.set(h.id, h.region)
    }
    const counts = new Map<string, number>()
    for (const u of filteredUsage) {
      const region = u.hotelId ? hotelRegionMap.get(u.hotelId) : undefined
      if (region) {
        counts.set(region, (counts.get(region) || 0) + 1)
      }
    }
    return Array.from(counts.entries())
      .map(([region, count]) => ({ region, count }))
      .sort((a, b) => b.count - a.count)
  }, [filteredUsage, hotels])

  // --- 施設別 Top15 ---
  const top15Data = useMemo(() => {
    const counts = new Map<string, number>()
    for (const u of filteredUsage) {
      counts.set(u.hotelName, (counts.get(u.hotelName) || 0) + 1)
    }
    return Array.from(counts.entries())
      .map(([name, count]) => ({ name: name.length > 15 ? name.slice(0, 15) + '…' : name, fullName: name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 15)
  }, [filteredUsage])

  // --- 年別利用推移 ---
  const yearlyData = useMemo(() => {
    const counts = new Map<number, number>()
    for (const u of filteredUsage) {
      if (u.year) {
        counts.set(u.year, (counts.get(u.year) || 0) + 1)
      }
    }
    return Array.from(counts.entries())
      .map(([year, count]) => ({ year, count }))
      .sort((a, b) => a.year - b.year)
  }, [filteredUsage])

  // --- 面積分布 ---
  const areaDistribution = useMemo(() => {
    const buckets = [
      { label: '〜100', min: 0, max: 100 },
      { label: '100〜200', min: 100, max: 200 },
      { label: '200〜300', min: 200, max: 300 },
      { label: '300〜500', min: 300, max: 500 },
      { label: '500〜1000', min: 500, max: 1000 },
      { label: '1000〜', min: 1000, max: Infinity },
    ]
    const data = buckets.map(b => ({ label: b.label, count: 0 }))
    for (const r of results) {
      for (const room of r.hotel.rooms) {
        if (room.areaSqm) {
          const idx = buckets.findIndex(b => room.areaSqm! >= b.min && room.areaSqm! < b.max)
          if (idx >= 0) data[idx].count++
        }
      }
    }
    return data
  }, [results])

  // --- キャパシティ分布 ---
  const capacityDistribution = useMemo(() => {
    const buckets = [
      { label: '〜50', min: 0, max: 50 },
      { label: '50〜100', min: 50, max: 100 },
      { label: '100〜200', min: 100, max: 200 },
      { label: '200〜500', min: 200, max: 500 },
      { label: '500〜1000', min: 500, max: 1000 },
      { label: '1000〜', min: 1000, max: Infinity },
    ]
    const data = buckets.map(b => ({ label: b.label, count: 0 }))
    for (const r of results) {
      for (const room of r.hotel.rooms) {
        const cap = room.capacity.theater
        if (cap) {
          const idx = buckets.findIndex(b => cap >= b.min && cap < b.max)
          if (idx >= 0) data[idx].count++
        }
      }
    }
    return data
  }, [results])

  // --- 散布図 ---
  const scatterData = useMemo(() => {
    const points: { area: number; capacity: number; name: string; hotel: string; region: string }[] = []
    for (const r of results) {
      for (const room of r.hotel.rooms) {
        if (room.areaSqm && room.capacity.theater) {
          points.push({
            area: room.areaSqm,
            capacity: room.capacity.theater,
            name: room.name,
            hotel: r.hotel.name,
            region: r.hotel.region,
          })
        }
      }
    }
    return points
  }, [results])

  const scatterByRegion = useMemo(() => {
    const grouped = new Map<string, typeof scatterData>()
    for (const p of scatterData) {
      const arr = grouped.get(p.region) || []
      arr.push(p)
      grouped.set(p.region, arr)
    }
    return Array.from(grouped.entries())
  }, [scatterData])

  return (
    <div className="p-4 space-y-6 overflow-y-auto">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard icon={Building2} label="施設数" value={kpi.venues} />
        <KpiCard icon={DoorOpen} label="部屋数" value={kpi.rooms} />
        <KpiCard icon={FileText} label="利用件数" value={kpi.usages} />
        <KpiCard icon={MapPin} label="地域数" value={kpi.regions} />
      </div>

      {/* 地域別利用件数 */}
      <ChartCard title="地域別利用件数">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={regionUsageData} layout="vertical" margin={{ left: 60, right: 20, top: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis type="category" dataKey="region" width={55} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="count" name="利用件数" radius={[0, 4, 4, 0]}>
              {regionUsageData.map((entry) => (
                <Cell key={entry.region} fill={REGION_COLORS[entry.region] || '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* 2列: Top15 + 年別推移 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="利用数Top15施設">
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={top15Data} layout="vertical" margin={{ left: 100, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="name" width={95} tick={{ fontSize: 11 }} />
              <Tooltip
                content={({ payload, label }) => {
                  if (!payload?.length) return null
                  const item = top15Data.find(d => d.name === label)
                  return (
                    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2 text-xs">
                      <div className="font-semibold">{item?.fullName || label}</div>
                      <div>利用件数: {payload[0].value}</div>
                    </div>
                  )
                }}
              />
              <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="年別利用推移">
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={yearlyData} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line type="monotone" dataKey="count" name="利用件数" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* 2列: 面積分布 + キャパシティ分布 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="面積分布（㎡）">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={areaDistribution} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" name="部屋数" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="キャパシティ分布（シアター形式）">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={capacityDistribution} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" name="部屋数" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* 散布図 */}
      <ChartCard title="面積 × キャパシティ散布図（地域別色分け）">
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" dataKey="area" name="面積（㎡）" tick={{ fontSize: 12 }} />
            <YAxis type="number" dataKey="capacity" name="キャパシティ" tick={{ fontSize: 12 }} />
            <Tooltip
              content={({ payload }) => {
                if (!payload?.length) return null
                const d = payload[0].payload
                return (
                  <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2 text-xs">
                    <div className="font-semibold">{d.hotel}</div>
                    <div className="text-gray-600">{d.name}</div>
                    <div>面積: {d.area}㎡ / キャパ: {d.capacity}名</div>
                  </div>
                )
              }}
            />
            <Legend />
            {scatterByRegion.map(([region, data]) => (
              <Scatter key={region} name={region} data={data} fill={REGION_COLORS[region] || '#94a3b8'} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      {children}
    </div>
  )
}
