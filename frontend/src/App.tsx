import { useEffect, useState } from 'react'
import { ChatPanel } from './components/ChatPanel'
import { MemberDetail } from './components/MemberDetail'
import { RosterPanel } from './components/RosterPanel'
import { TeamSearchPanel } from './components/TeamSearchPanel'
import { UploadHistoryPanel } from './components/UploadHistoryPanel'
import { UploadModal } from './components/UploadModal'
import type { MemberSelectContext } from './rosterQuery'
import type { MemberOut } from './types'

type View = 'roster' | 'history' | 'member'
type SearchTab = 'roster' | 'team'

export default function App() {
  const [rosterRefreshKey, setRosterRefreshKey] = useState(0)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [view, setView] = useState<View>('roster')
  const [searchTab, setSearchTab] = useState<SearchTab>('roster')
  const [selected, setSelected] = useState<MemberOut | null>(null)
  const [selectContext, setSelectContext] = useState<MemberSelectContext | null>(null)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 8)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  function handleRosterChanged() {
    setRosterRefreshKey((k) => k + 1)
    setSelected(null)
    setSelectContext(null)
    setView('roster')
  }

  function handleSelectMember(member: MemberOut, context: MemberSelectContext) {
    setSelected(member)
    setSelectContext(context)
    setView('member')
  }

  function handleSelectPeer(member: MemberOut) {
    setSelected(member)
  }

  function handleBackToRoster() {
    setSelected(null)
    setSelectContext(null)
    setView('roster')
  }

  const showRosterActions = view === 'roster'
  const onSearchSurface = view === 'roster'

  return (
    <div className="app">
      <header className={scrolled ? 'topbar topbar-scrolled' : 'topbar'}>
        <div className="brand">
          <p className="brand-mark">Paratus</p>
        </div>
        <div className="topbar-actions">
          <button
            type="button"
            className={chatOpen ? 'secondary chat-toggle-active' : 'secondary'}
            onClick={() => setChatOpen((open) => !open)}
            aria-expanded={chatOpen}
            aria-controls="chat-dock"
          >
            Ask
          </button>
          {showRosterActions && (
            <>
              <button type="button" className="secondary" onClick={() => setView('history')}>
                Upload history
              </button>
              <button type="button" className="primary" onClick={() => setUploadOpen(true)}>
                Upload
              </button>
            </>
          )}
        </div>
      </header>

      <main>
        {view === 'member' && selected && selectContext && (
          <MemberDetail
            member={selected}
            context={selectContext}
            onSelectPeer={handleSelectPeer}
            onBack={handleBackToRoster}
          />
        )}
        {view === 'history' && (
          <UploadHistoryPanel
            refreshKey={rosterRefreshKey}
            onBack={handleBackToRoster}
            onRosterCleared={handleRosterChanged}
          />
        )}
        <div className={!onSearchSurface ? 'view-hidden' : undefined} aria-hidden={!onSearchSurface}>
          <div className="search-tabs" role="tablist" aria-label="Search mode">
            <div className="tabs">
              <button
                type="button"
                role="tab"
                className={searchTab === 'roster' ? 'tab active' : 'tab'}
                aria-selected={searchTab === 'roster'}
                onClick={() => setSearchTab('roster')}
              >
                Roster
              </button>
              <button
                type="button"
                role="tab"
                className={searchTab === 'team' ? 'tab active' : 'tab'}
                aria-selected={searchTab === 'team'}
                onClick={() => setSearchTab('team')}
              >
                Team search
              </button>
            </div>
          </div>

          <div
            className={searchTab !== 'roster' ? 'view-hidden' : undefined}
            aria-hidden={searchTab !== 'roster'}
            role="tabpanel"
          >
            <RosterPanel refreshKey={rosterRefreshKey} onSelectMember={handleSelectMember} />
          </div>

          <div
            className={searchTab !== 'team' ? 'view-hidden' : undefined}
            aria-hidden={searchTab !== 'team'}
            role="tabpanel"
          >
            <TeamSearchPanel refreshKey={rosterRefreshKey} />
          </div>
        </div>
      </main>

      {uploadOpen && (
        <UploadModal
          onClose={() => setUploadOpen(false)}
          onRosterChanged={handleRosterChanged}
        />
      )}

      <div id="chat-dock">
        <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />
      </div>
    </div>
  )
}
