import { Building2 } from 'lucide-react'

export function Header() {
  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 sticky top-0 z-30">
      <div className="max-w-[1800px] mx-auto flex items-center gap-3">
        <Building2 className="w-6 h-6 text-blue-600 shrink-0" />
        <h1 className="text-lg font-bold text-gray-900">ホテル宴会場検索</h1>
      </div>
    </header>
  )
}
