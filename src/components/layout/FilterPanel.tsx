import { SlidersHorizontal, RotateCcw } from 'lucide-react'
import { useVenueStore } from '../../store/venueStore'
import type { Region, CapacityType } from '../../types'

const regions: Region[] = ['東京', '大阪', '名古屋', '福岡', '京都', '横浜', '神戸', '札幌', '仙台', '千葉']
const capacityTypes: { value: CapacityType; label: string }[] = [
  { value: 'theater', label: 'シアター' },
  { value: 'school', label: 'スクール' },
  { value: 'banquet', label: '着席' },
  { value: 'standing', label: '立食' },
]

function NumberInput({ value, onChange, placeholder }: {
  value: number | undefined
  onChange: (v: number | undefined) => void
  placeholder: string
}) {
  return (
    <input
      type="number"
      value={value ?? ''}
      onChange={e => {
        const n = e.target.value ? Number(e.target.value) : undefined
        onChange(n && n > 0 ? n : undefined)
      }}
      placeholder={placeholder}
      className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
    />
  )
}

export function FilterPanel({ className = '' }: { className?: string }) {
  const filter = useVenueStore(s => s.filter)
  const toggleRegion = useVenueStore(s => s.toggleRegion)
  const setAreaMin = useVenueStore(s => s.setAreaMin)
  const setAreaMax = useVenueStore(s => s.setAreaMax)
  const setCeilingMin = useVenueStore(s => s.setCeilingMin)
  const setCeilingMax = useVenueStore(s => s.setCeilingMax)
  const setCapacityMin = useVenueStore(s => s.setCapacityMin)
  const setCapacityMax = useVenueStore(s => s.setCapacityMax)
  const setCapacityType = useVenueStore(s => s.setCapacityType)
  const setHasDivisions = useVenueStore(s => s.setHasDivisions)
  const setHasUsageRecords = useVenueStore(s => s.setHasUsageRecords)
  const resetFilters = useVenueStore(s => s.resetFilters)

  return (
    <aside className={`bg-white border-r border-gray-200 p-4 space-y-5 overflow-y-auto ${className}`}>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-1.5">
          <SlidersHorizontal className="w-4 h-4" />
          フィルタ
        </h2>
        <button
          onClick={resetFilters}
          className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <RotateCcw className="w-3 h-3" />
          リセット
        </button>
      </div>

      {/* Region */}
      <section>
        <h3 className="text-xs font-semibold text-gray-500 mb-2">地域</h3>
        <div className="flex flex-wrap gap-1.5">
          {regions.map(r => (
            <button
              key={r}
              onClick={() => toggleRegion(r)}
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                filter.regions.includes(r)
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </section>

      {/* Area */}
      <section>
        <h3 className="text-xs font-semibold text-gray-500 mb-2">面積 (㎡)</h3>
        <div className="flex items-center gap-2">
          <NumberInput value={filter.areaMin} onChange={setAreaMin} placeholder="下限" />
          <span className="text-gray-400 text-xs">〜</span>
          <NumberInput value={filter.areaMax} onChange={setAreaMax} placeholder="上限" />
        </div>
      </section>

      {/* Ceiling */}
      <section>
        <h3 className="text-xs font-semibold text-gray-500 mb-2">天井高 (m)</h3>
        <div className="flex items-center gap-2">
          <NumberInput value={filter.ceilingMin} onChange={setCeilingMin} placeholder="下限" />
          <span className="text-gray-400 text-xs">〜</span>
          <NumberInput value={filter.ceilingMax} onChange={setCeilingMax} placeholder="上限" />
        </div>
      </section>

      {/* Capacity */}
      <section>
        <h3 className="text-xs font-semibold text-gray-500 mb-2">収容人数</h3>
        <div className="flex flex-wrap gap-1 mb-2">
          {capacityTypes.map(ct => {
            const isActive = filter.capacityMin != null || filter.capacityMax != null
            const isSelected = filter.capacityType === ct.value
            return (
              <button
                key={ct.value}
                onClick={() => setCapacityType(ct.value)}
                className={`px-2 py-0.5 text-xs rounded border transition-colors ${
                  isSelected && isActive
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                }`}
              >
                {ct.label}
              </button>
            )
          })}
        </div>
        <div className="flex items-center gap-2">
          <NumberInput value={filter.capacityMin} onChange={setCapacityMin} placeholder="下限" />
          <span className="text-gray-400 text-xs">〜</span>
          <NumberInput value={filter.capacityMax} onChange={setCapacityMax} placeholder="上限" />
        </div>
      </section>

      {/* Divisions */}
      <section>
        <h3 className="text-xs font-semibold text-gray-500 mb-2">分割可能</h3>
        <div className="flex gap-1.5">
          {([
            { value: null, label: '全て' },
            { value: true, label: '可能' },
            { value: false, label: 'なし' },
          ] as const).map(opt => (
            <button
              key={String(opt.value)}
              onClick={() => setHasDivisions(opt.value)}
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                filter.hasDivisions === opt.value
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </section>

      {/* Usage records */}
      <section>
        <h3 className="text-xs font-semibold text-gray-500 mb-2">利用実績</h3>
        <div className="flex gap-1.5">
          {([
            { value: null, label: '全て' },
            { value: true, label: '実績あり' },
          ] as const).map(opt => (
            <button
              key={String(opt.value)}
              onClick={() => setHasUsageRecords(opt.value)}
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                filter.hasUsageRecords === opt.value
                  ? 'bg-emerald-600 text-white border-emerald-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-emerald-400'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </section>
    </aside>
  )
}
