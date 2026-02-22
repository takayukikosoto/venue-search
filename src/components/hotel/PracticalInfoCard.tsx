import { Truck, Wifi, Monitor, Train, Phone, ParkingCircle, ExternalLink, FileText, Map } from 'lucide-react'
import type { PracticalInfo } from '../../types'

const infoFields: { key: keyof PracticalInfo; icon: typeof Wifi; label: string }[] = [
  { key: 'nearestStation', icon: Train, label: '最寄駅' },
  { key: 'wifi', icon: Wifi, label: 'Wi-Fi' },
  { key: 'avEquipment', icon: Monitor, label: 'AV設備' },
  { key: 'loadingDockSize', icon: Truck, label: '搬入口' },
  { key: 'parking', icon: ParkingCircle, label: '駐車場' },
  { key: 'contactPhone', icon: Phone, label: '宴会予約TEL' },
]

const linkFields: { key: keyof PracticalInfo; icon: typeof ExternalLink; label: string }[] = [
  { key: 'venuePageUrl', icon: ExternalLink, label: '会場ページ' },
  { key: 'floorPlanUrl', icon: Map, label: 'フロアプラン' },
  { key: 'brochureUrl', icon: FileText, label: 'パンフレット' },
]

export function PracticalInfoCard({ info }: { info: PracticalInfo }) {
  const entries = infoFields.filter(f => info[f.key])
  const links = linkFields.filter(f => info[f.key])
  if (entries.length === 0 && links.length === 0) return null

  return (
    <div className="mt-3 pt-3 border-t border-gray-200 space-y-1.5">
      {entries.map(({ key, icon: Icon, label }) => (
        <div key={key} className="flex items-start gap-2 text-xs">
          <Icon className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
          <div>
            <span className="font-medium text-gray-500">{label}: </span>
            <span className="text-gray-700">{info[key]}</span>
          </div>
        </div>
      ))}
      {links.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {links.map(({ key, icon: Icon, label }) => (
            <a
              key={key}
              href={info[key]}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2 py-1 text-xs text-blue-600 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
            >
              <Icon className="w-3 h-3" />
              {label}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
