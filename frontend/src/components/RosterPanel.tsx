import { useEffect, useState, type FormEvent } from 'react'
import { getAfscSearchLabels, isAbortError, listMembers } from '../api'
import {
  PAGE_SIZE,
  emptyRosterFilters,
  type MemberSelectContext,
  type RosterFilters,
} from '../rosterQuery'
import type { MemberOut, PersonnelType } from '../types'
import { AfscDetailedSearch } from './AfscDetailedSearch'
import { MembersTable } from './MembersTable'

interface RosterPanelProps {
  refreshKey: number
  onSelectMember: (member: MemberOut, context: MemberSelectContext) => void
}

function PaginationBar({
  from,
  to,
  total,
  page,
  pageCount,
  loading,
  onPrev,
  onNext,
}: {
  from: number
  to: number
  total: number
  page: number
  pageCount: number
  loading: boolean
  onPrev: () => void
  onNext: () => void
}) {
  return (
    <div className="pagination">
      <p className="muted count">
        Showing {from}–{to} of {total}
      </p>
      <div className="filter-actions">
        <button type="button" className="secondary" disabled={page <= 0 || loading} onClick={onPrev}>
          Previous
        </button>
        <span className="muted page-indicator">
          Page {page + 1} / {pageCount}
        </span>
        <button
          type="button"
          className="secondary"
          disabled={page + 1 >= pageCount || loading}
          onClick={() => onNext()}
        >
          Next
        </button>
      </div>
    </div>
  )
}

export function RosterPanel({ refreshKey, onSelectMember }: RosterPanelProps) {
  const [name, setName] = useState('')
  const [dodid, setDodid] = useState('')
  const [afsc, setAfsc] = useState('')
  const [personnelType, setPersonnelType] = useState<PersonnelType | ''>('')
  const [applied, setApplied] = useState<RosterFilters>(emptyRosterFilters)
  const [page, setPage] = useState(0)
  const [members, setMembers] = useState<MemberOut[]>([])
  const [total, setTotal] = useState(0)
  const [searchLabels, setSearchLabels] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const result = await listMembers(
          {
            name: applied.name || undefined,
            dodid: applied.dodid || undefined,
            afsc: applied.afsc || undefined,
            personnel_type: applied.personnel_type || undefined,
            limit: PAGE_SIZE,
            offset: page * PAGE_SIZE,
          },
          { signal },
        )
        if (signal.aborted) return

        setMembers(result.members)
        setTotal(result.total)

        if (applied.afsc) {
          try {
            const resolved = await getAfscSearchLabels(applied.afsc, { signal })
            if (signal.aborted) return
            setSearchLabels(resolved.labels ?? [])
          } catch (err: unknown) {
            if (signal.aborted || isAbortError(err)) return
            setSearchLabels([])
          }
        } else {
          setSearchLabels([])
        }
      } catch (err: unknown) {
        if (signal.aborted || isAbortError(err)) return
        setMembers([])
        setTotal(0)
        setSearchLabels([])
        setError(err instanceof Error ? err.message : 'Failed to load members')
      } finally {
        if (!signal.aborted) setLoading(false)
      }
    }

    void load()
    return () => controller.abort()
  }, [applied, page, refreshKey])

  function selectMember(member: MemberOut) {
    onSelectMember(member, {
      searchLabels,
      filters: applied,
      page,
    })
  }

  function handleApply(event: FormEvent) {
    event.preventDefault()
    setPage(0)
    setApplied({
      name: name.trim(),
      dodid: dodid.trim(),
      afsc: afsc.trim(),
      personnel_type: personnelType,
    })
  }

  function handleClear() {
    setName('')
    setDodid('')
    setAfsc('')
    setPersonnelType('')
    setPage(0)
    setApplied(emptyRosterFilters())
  }

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const from = total === 0 ? 0 : page * PAGE_SIZE + 1
  const to = Math.min(total, (page + 1) * PAGE_SIZE)

  return (
    <section className="panel">
      <h2>Roster</h2>

      <form className="filters" onSubmit={handleApply}>
        <label>
          Name
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Jane"
          />
        </label>
        <label>
          DODID
          <input
            type="text"
            value={dodid}
            onChange={(e) => setDodid(e.target.value)}
            placeholder="Exact match"
          />
        </label>
        <label>
          AFSC
          <input
            type="text"
            value={afsc}
            onChange={(e) => setAfsc(e.target.value)}
            placeholder="e.g. 1A1X2"
          />
        </label>
        <label>
          Type
          <select
            value={personnelType}
            onChange={(e) => setPersonnelType(e.target.value as PersonnelType | '')}
          >
            <option value="">All</option>
            <option value="enlisted">Enlisted</option>
            <option value="officer">Officer</option>
          </select>
        </label>
        <div className="filter-actions">
          <button type="submit" className="primary">
            Apply
          </button>
          <button type="button" className="secondary" onClick={handleClear}>
            Clear
          </button>
        </div>
      </form>

      <AfscDetailedSearch
        afsc={afsc}
        personnelType={personnelType}
        onAfscChange={setAfsc}
      />

      {searchLabels.length > 0 && (
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

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading members…</p>}

      {!loading && !error && members.length === 0 && (
        <p className="muted">No members match the current filters.</p>
      )}

      {members.length > 0 && (
        <>
          <PaginationBar
            from={from}
            to={to}
            total={total}
            page={page}
            pageCount={pageCount}
            loading={loading}
            onPrev={() => setPage((p) => Math.max(0, p - 1))}
            onNext={() => setPage((p) => p + 1)}
          />

          <MembersTable
            members={members}
            searchLabels={searchLabels}
            onSelectMember={selectMember}
          />

          <PaginationBar
            from={from}
            to={to}
            total={total}
            page={page}
            pageCount={pageCount}
            loading={loading}
            onPrev={() => setPage((p) => Math.max(0, p - 1))}
            onNext={() => setPage((p) => p + 1)}
          />
        </>
      )}
    </section>
  )
}
