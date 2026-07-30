import { useEffect, useState } from 'react'
import { isAbortError, listMembers } from '../api'
import { labelMatchesSearch } from '../labelMatch'
import {
  PAGE_SIZE,
  filtersHaveSearch,
  toMemberFilters,
  type MemberSelectContext,
} from '../rosterQuery'
import type { MemberOut } from '../types'
import { MembersTable } from './MembersTable'

interface MemberDetailProps {
  member: MemberOut
  context: MemberSelectContext
  onSelectPeer: (member: MemberOut) => void
  onBack: () => void
}

export function MemberDetail({ member, context, onSelectPeer, onBack }: MemberDetailProps) {
  const [peers, setPeers] = useState<MemberOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(context.page)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const searchLabels = context.searchLabels
  const created =
    member.created_at != null ? new Date(member.created_at).toLocaleString() : null
  const labels =
    member.afsc_labels?.length > 0
      ? member.afsc_labels
      : member.afsc_label
        ? member.afsc_label.split(',').map((s) => s.trim()).filter(Boolean)
        : []

  const fromSearch = filtersHaveSearch(context.filters)
  const peerTitle = fromSearch ? 'Search results' : 'Same AFSC family'

  useEffect(() => {
    setPage(context.page)
  }, [context.page, context.filters])

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller

    async function loadPeers() {
      setLoading(true)
      setError(null)
      try {
        const result = await listMembers(
          toMemberFilters(context.filters, page, member.afsc_family),
          { signal },
        )
        if (signal.aborted) return
        setPeers(result.members)
        setTotal(result.total)
      } catch (err: unknown) {
        if (signal.aborted || isAbortError(err)) return
        setPeers([])
        setTotal(0)
        setError(err instanceof Error ? err.message : 'Failed to load related members')
      } finally {
        if (!signal.aborted) setLoading(false)
      }
    }

    void loadPeers()
    return () => controller.abort()
  }, [context.filters, page, member.afsc_family])

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const from = total === 0 ? 0 : page * PAGE_SIZE + 1
  const to = Math.min(total, (page + 1) * PAGE_SIZE)

  return (
    <div className="member-detail-view">
      <section className="panel member-detail">
        <div className="member-topbar">
          <button type="button" className="secondary back-btn" onClick={onBack}>
            ← Back to roster
          </button>
          {created && (
            <p className="muted member-updated">
              Added <span>{created}</span>
            </p>
          )}
        </div>

        <header className="member-hero">
          <div className="member-hero-title">
            <h2 className="member-name">{member.display_name}</h2>
            {member.personnel_type && (
              <span className={`type-pill type-${member.personnel_type}`}>
                {member.personnel_type.toUpperCase()}
              </span>
            )}
          </div>
          {member.rank && <p className="member-rank muted">{member.rank}</p>}
        </header>

        <div className="member-fields-row">
          <section className="member-section member-section-afsc">
            <h3 className="member-section-label">AFSC</h3>
            <div className="member-afsc-row">
              <code className="member-afsc-code">{member.normalized_afsc}</code>
              {member.afsc !== member.normalized_afsc && (
                <span className="muted member-afsc-raw">raw {member.afsc}</span>
              )}
              {labels.length > 0 && (
                <div className="label-pills member-label-pills">
                  {labels.map((label) => {
                    const active =
                      searchLabels.length > 0 && labelMatchesSearch(label, searchLabels)
                    return (
                      <span
                        key={label}
                        className={active ? 'label-pill label-pill-active' : 'label-pill'}
                      >
                        {label}
                      </span>
                    )
                  })}
                </div>
              )}
            </div>
          </section>

          <section className="member-section member-section-dodid">
            <h3 className="member-section-label">DODID</h3>
            <div className="member-afsc-row">
              <code className="member-afsc-code">{member.dodid}</code>
            </div>
          </section>
        </div>
      </section>

      <section className="panel member-peers">
        <h3 className="member-peers-title">{peerTitle}</h3>
        {fromSearch && searchLabels.length > 0 && (
          <div className="search-labels">
            <span className="muted search-labels-caption">Matching labels</span>
            <div className="label-pills">
              {searchLabels.map((label) => (
                <span key={label} className="label-pill label-pill-active">
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}
        {!fromSearch && member.afsc_family && (
          <p className="muted member-peers-caption">
            Members matching family <code>{member.afsc_family}</code>
          </p>
        )}

        {error && <p className="error">{error}</p>}
        {loading && <p className="muted">Loading members…</p>}
        {!loading && !error && peers.length === 0 && (
          <p className="muted">No related members found.</p>
        )}

        {peers.length > 0 && (
          <>
            <div className="pagination">
              <p className="muted count">
                Showing {from}–{to} of {total}
              </p>
              <div className="filter-actions">
                <button
                  type="button"
                  className="secondary"
                  disabled={page <= 0 || loading}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  Previous
                </button>
                <span className="muted page-indicator">
                  Page {page + 1} / {pageCount}
                </span>
                <button
                  type="button"
                  className="secondary"
                  disabled={page + 1 >= pageCount || loading}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>

            <MembersTable
              members={peers}
              searchLabels={searchLabels}
              activeMemberId={member.id}
              onSelectMember={onSelectPeer}
            />
          </>
        )}
      </section>
    </div>
  )
}
