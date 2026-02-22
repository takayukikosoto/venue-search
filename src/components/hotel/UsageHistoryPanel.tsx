import { useState } from 'react'
import { Calendar, Users, ChevronDown, ChevronUp } from 'lucide-react'
import type { UsageRecord } from '../../types'

export function UsageHistoryPanel({ records }: { records: UsageRecord[] }) {
  const [showAll, setShowAll] = useState(false)
  const sorted = [...records].sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''))
  const displayed = showAll ? sorted : sorted.slice(0, 5)

  if (records.length === 0) return null

  return (
    <div className="mt-3 border-t border-gray-200 pt-3">
      <h4 className="text-xs font-semibold text-gray-500 mb-2">
        利用実績 ({records.length}件)
      </h4>
      <div className="space-y-1.5">
        {displayed.map(r => (
          <div key={r.id} className="flex items-start gap-2 text-xs text-gray-600 bg-gray-50 rounded px-2 py-1.5">
            <div className="flex-1 min-w-0">
              <div className="font-medium text-gray-800 truncate">{r.seminarName}</div>
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-0.5">
                {r.date && (
                  <span className="flex items-center gap-0.5">
                    <Calendar className="w-3 h-3 text-gray-400" />
                    {r.date}
                  </span>
                )}
                <span className="text-gray-500">{r.roomName}</span>
                {r.seatCount && (
                  <span className="flex items-center gap-0.5">
                    <Users className="w-3 h-3 text-gray-400" />
                    {r.seatCount}席
                  </span>
                )}
                {r.attendeeEstimate && (
                  <span className="text-gray-500">参加者≈{r.attendeeEstimate}名</span>
                )}
              </div>
              {r.greenRooms && r.greenRooms.length > 0 && (
                <div className="mt-0.5 text-gray-400">
                  控室: {r.greenRooms.map(g => g.name).join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      {records.length > 5 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="mt-1.5 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
        >
          {showAll ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {showAll ? '折りたたむ' : `残り ${records.length - 5} 件を表示`}
        </button>
      )}
    </div>
  )
}
