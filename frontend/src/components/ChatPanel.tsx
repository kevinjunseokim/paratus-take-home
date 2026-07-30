import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { isAbortError, sendChat } from '../api'
import type { ChatMessage } from '../types'

const SUGGESTIONS = [
  'How many enlisted 1A1XX members are on the roster?',
  'What does AFSC 11M3K mean?',
  'Can we form a team with 1 officer 11MX and 2 enlisted 1A1XX?',
]

interface ChatPanelProps {
  open: boolean
  onClose: () => void
}

export function ChatPanel({ open, onClose }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!open) return
    const id = window.setTimeout(() => inputRef.current?.focus(), 50)
    return () => window.clearTimeout(id)
  }, [open])

  useEffect(() => {
    if (!open) return
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, loading, open])

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  async function ask(content: string) {
    const trimmed = content.trim()
    if (!trimmed || loading) return

    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: trimmed }]
    setMessages(nextMessages)
    setDraft('')
    setError(null)
    setLoading(true)

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await sendChat(nextMessages, { signal: controller.signal })
      if (controller.signal.aborted) return
      setMessages([...nextMessages, { role: 'assistant', content: response.reply }])
    } catch (err: unknown) {
      if (controller.signal.aborted || isAbortError(err)) return
      const message = err instanceof Error ? err.message : 'Chat request failed'
      setError(
        /OPENAI_API_KEY/i.test(message)
          ? 'Chat is unavailable until OPENAI_API_KEY is set in backend/.env.'
          : message,
      )
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void ask(draft)
  }

  function handleClear() {
    abortRef.current?.abort()
    setMessages([])
    setError(null)
    setLoading(false)
    setDraft('')
    inputRef.current?.focus()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void ask(draft)
    }
  }

  if (!open) return null

  return (
    <div className="chat-dock" role="dialog" aria-label="Roster assistant">
      <div className="chat-panel">
        <header className="chat-header">
          <div>
            <h2>Ask</h2>
          </div>
          <div className="chat-header-actions">
            <button
              type="button"
              className="secondary"
              onClick={handleClear}
              disabled={loading || (messages.length === 0 && !error)}
            >
              Clear
            </button>
            <button type="button" className="secondary" onClick={onClose} aria-label="Close chat">
              Close
            </button>
          </div>
        </header>

        <div className="chat-messages" ref={listRef}>
          {messages.length === 0 && !loading && (
            <div className="chat-empty">
              <p className="muted">Try a simple question:</p>
              <ul className="chat-suggestions">
                {SUGGESTIONS.map((text) => (
                  <li key={text}>
                    <button type="button" className="chat-suggestion" onClick={() => void ask(text)}>
                      {text}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={message.role === 'user' ? 'chat-bubble chat-bubble-user' : 'chat-bubble chat-bubble-assistant'}
            >
              <p>{message.content}</p>
            </div>
          ))}

          {loading && (
            <div className="chat-bubble chat-bubble-assistant chat-bubble-pending">
              <p className="muted">Checking the roster…</p>
            </div>
          )}
        </div>

        {error && <p className="error chat-error">{error}</p>}

        <form className="chat-composer" onSubmit={handleSubmit}>
          <textarea
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the active roster or a team…"
            rows={2}
            maxLength={4000}
            disabled={loading}
            aria-label="Message"
          />
          <button type="submit" className="primary" disabled={loading || !draft.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
