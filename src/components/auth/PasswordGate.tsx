import { useState, useCallback, type FormEvent } from 'react'
import { Lock } from 'lucide-react'

const HASH = '88453cd3db4797874b9be4c433738cb5d67fc24a02d04a89882bc95ecb0f3c44'
const STORAGE_KEY = 'venue-auth'

async function sha256(text: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('')
}

export function PasswordGate({ children }: { children: React.ReactNode }) {
  const [authed, setAuthed] = useState(() => sessionStorage.getItem(STORAGE_KEY) === HASH)
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)

  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    const hash = await sha256(password)
    if (hash === HASH) {
      sessionStorage.setItem(STORAGE_KEY, HASH)
      setAuthed(true)
    } else {
      setError(true)
      setTimeout(() => setError(false), 1500)
    }
  }, [password])

  if (authed) return <>{children}</>

  return (
    <div className="h-screen flex items-center justify-center bg-gray-50">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-8 w-80 space-y-4">
        <div className="flex flex-col items-center gap-2">
          <div className="p-3 bg-blue-50 rounded-full">
            <Lock className="w-6 h-6 text-blue-600" />
          </div>
          <h1 className="text-lg font-bold text-gray-900">会場検索システム</h1>
          <p className="text-xs text-gray-500">パスワードを入力してください</p>
        </div>
        <input
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder="パスワード"
          autoFocus
          className={`w-full px-3 py-2 border rounded-lg text-sm outline-none transition-colors ${
            error ? 'border-red-400 bg-red-50' : 'border-gray-300 focus:border-blue-500'
          }`}
        />
        {error && <p className="text-xs text-red-500 text-center">パスワードが違います</p>}
        <button
          type="submit"
          className="w-full py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          ログイン
        </button>
      </form>
    </div>
  )
}
