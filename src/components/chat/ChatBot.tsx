import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageCircle, X, Send, Loader2 } from 'lucide-react'
import { GoogleGenerativeAI } from '@google/generative-ai'
import { useVenueStore } from '../../store/venueStore'

interface Message {
  role: 'user' | 'model'
  text: string
}

const SYSTEM_PROMPT = `あなたは会場検索システムのアシスタントです。ユーザーの質問に日本語で簡潔に答えてください。
会場データに関する質問には、提供されたコンテキストを使って回答してください。
それ以外の一般的な質問にも対応できます。`

function buildContext(hotels: { name: string; region: string; rooms: { name: string; areaSqm?: number; capacity: { theater?: number } }[] }[]) {
  const summary = hotels.slice(0, 30).map(h => {
    const rooms = h.rooms.slice(0, 5).map(r =>
      `${r.name}(${r.areaSqm ?? '?'}㎡, ${r.capacity.theater ?? '?'}名)`
    ).join(', ')
    return `${h.name}[${h.region}]: ${rooms}${h.rooms.length > 5 ? ` 他${h.rooms.length - 5}室` : ''}`
  }).join('\n')
  return `\n\n【会場データ（一部）】\n${summary}\n（全${hotels.length}施設）`
}

export function ChatBot() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const hotels = useVenueStore(s => s.hotels)

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight)
  }, [messages])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const send = useCallback(async () => {
    const text = input.trim()
    if (!text || loading) return

    const apiKey = import.meta.env.VITE_GEMINI_API_KEY
    if (!apiKey) {
      setMessages(prev => [...prev, { role: 'user', text }, { role: 'model', text: 'APIキーが設定されていません。VITE_GEMINI_API_KEY を .env.local に設定してください。' }])
      setInput('')
      return
    }

    const userMsg: Message = { role: 'user', text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const genAI = new GoogleGenerativeAI(apiKey)
      const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' })

      const context = buildContext(hotels)
      const history = messages.map(m => ({
        role: m.role,
        parts: [{ text: m.text }],
      }))

      const chat = model.startChat({
        history: [
          { role: 'user', parts: [{ text: SYSTEM_PROMPT + context }] },
          { role: 'model', parts: [{ text: 'はい、会場検索システムのアシスタントとして対応します。何でもお聞きください。' }] },
          ...history,
        ],
      })

      const result = await chat.sendMessage(text)
      const reply = result.response.text()
      setMessages(prev => [...prev, { role: 'model', text: reply }])
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'エラーが発生しました'
      setMessages(prev => [...prev, { role: 'model', text: `エラー: ${errMsg}` }])
    } finally {
      setLoading(false)
    }
  }, [input, loading, messages, hotels])

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-40 p-3 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-colors"
        >
          <MessageCircle className="w-6 h-6" />
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-5 right-5 z-40 w-80 sm:w-96 h-[28rem] bg-white rounded-xl shadow-2xl border border-gray-200 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-blue-600 rounded-t-xl">
            <span className="text-sm font-semibold text-white">AI アシスタント</span>
            <button onClick={() => setOpen(false)} className="text-white/80 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
            {messages.length === 0 && (
              <p className="text-xs text-gray-400 text-center mt-8">会場のことでも何でも聞いてください</p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                  m.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}>
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="px-3 py-2 bg-gray-100 rounded-lg">
                  <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <form
            onSubmit={e => { e.preventDefault(); send() }}
            className="p-2 border-t border-gray-200 flex gap-2"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="メッセージを入力..."
              className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40 transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </>
  )
}
