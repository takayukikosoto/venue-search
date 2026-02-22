import { X } from 'lucide-react'
import { useVenueStore } from '../../store/venueStore'
import { formatArea, formatCeiling, formatCapacity } from '../../utils/format'
import type { Hotel, Room } from '../../types'

interface ComparisonRow {
  label: string
  getValue: (hotel: Hotel, room: Room) => string | number | undefined
  isNumeric?: boolean
}

const rows: ComparisonRow[] = [
  { label: 'ホテル名', getValue: (h) => h.name },
  { label: '会場名', getValue: (_, r) => r.name },
  { label: '地域', getValue: (h) => h.region },
  { label: '面積', getValue: (_, r) => r.areaSqm, isNumeric: true },
  { label: '天井高', getValue: (_, r) => r.ceilingHeightM, isNumeric: true },
  { label: 'シアター', getValue: (_, r) => r.capacity.theater ?? r.capacity.max, isNumeric: true },
  { label: 'スクール', getValue: (_, r) => r.capacity.school, isNumeric: true },
  { label: '着席', getValue: (_, r) => r.capacity.banquet, isNumeric: true },
  { label: '立食', getValue: (_, r) => r.capacity.standing, isNumeric: true },
  { label: '分割', getValue: (_, r) => r.divisions.length > 0 ? `${r.divisions.length}分割可` : 'なし' },
  { label: '利用実績', getValue: (h) => h.usageCount ?? 0, isNumeric: true },
  { label: '部屋実績', getValue: (_, r) => r.usageCount ?? 0, isNumeric: true },
  { label: '典型席数', getValue: (_, r) => r.typicalSeatCount, isNumeric: true },
  { label: 'Wi-Fi', getValue: (h) => h.practicalInfo?.wifi ?? '—' },
  { label: '搬入口', getValue: (h) => h.practicalInfo?.loadingDockSize ?? '—' },
  { label: '駐車場', getValue: (h) => h.practicalInfo?.parking ?? '—' },
]

function formatValue(row: ComparisonRow, value: string | number | undefined): string {
  if (value == null) return '—'
  if (typeof value === 'string') return value
  if (row.label === '面積') return formatArea(value)
  if (row.label === '天井高') return formatCeiling(value)
  if (row.label === '利用実績' || row.label === '部屋実績') return `${value}件`
  if (row.label === '典型席数') return `${value}席`
  return formatCapacity(value)
}

export function ComparisonTable() {
  const comparisonRooms = useVenueStore(s => s.comparisonRooms)
  const setShowComparison = useVenueStore(s => s.setShowComparison)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowComparison(false)}>
      <div
        className="bg-white rounded-2xl max-w-[95vw] w-full max-h-[90vh] overflow-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4 flex items-center justify-between rounded-t-2xl z-10">
          <h2 className="text-lg font-bold">会場比較</h2>
          <button onClick={() => setShowComparison(false)} className="p-1 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left py-2 px-3 bg-gray-50 font-medium text-gray-500 sticky left-0 min-w-[100px]">項目</th>
                {comparisonRooms.map(({ hotel, room }) => (
                  <th key={`${hotel.id}:${room.id}`} className="text-left py-2 px-3 bg-gray-50 font-medium min-w-[150px]">
                    <div className="text-gray-900">{room.name}</div>
                    <div className="text-xs text-gray-500 font-normal">{hotel.name}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(row => {
                const values = comparisonRooms.map(({ hotel, room }) => row.getValue(hotel, room))
                const numericValues = row.isNumeric
                  ? values.filter((v): v is number => typeof v === 'number')
                  : []
                const maxVal = numericValues.length > 0 ? Math.max(...numericValues) : null

                return (
                  <tr key={row.label} className="border-t border-gray-100">
                    <td className="py-2 px-3 font-medium text-gray-500 sticky left-0 bg-white">{row.label}</td>
                    {values.map((v, i) => {
                      const isMax = row.isNumeric && typeof v === 'number' && v === maxVal && numericValues.length > 1
                      return (
                        <td
                          key={i}
                          className={`py-2 px-3 ${isMax ? 'text-blue-700 font-semibold bg-blue-50' : 'text-gray-700'}`}
                        >
                          {formatValue(row, v)}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
