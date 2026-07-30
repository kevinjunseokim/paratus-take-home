import { useEffect, useState, type FormEvent } from 'react'
import { checkTeam, isAbortError } from '../api'
import {
  createTeamRequirement,
  emptyTeamRequirements,
  formatRequirementLabel,
  requirementToCheckPayload,
  type TeamRequirement,
  type TeamRequirementResult,
  type TeamSearchResults,
} from '../teamQuery'
import type { PersonnelType } from '../types'

interface TeamSearchPanelProps {
  refreshKey: number
}

export function TeamSearchPanel({ refreshKey }: TeamSearchPanelProps) {
  const [requirements, setRequirements] = useState<TeamRequirement[]>(emptyTeamRequirements)
  const [applied, setApplied] = useState<TeamRequirement[] | null>(null)
  const [results, setResults] = useState<TeamSearchResults | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!applied) return

    const controller = new AbortController()
    const { signal } = controller

    async function run() {
      setLoading(true)
      setError(null)
      try {
        const response = await checkTeam(
          { requirements: applied.map(requirementToCheckPayload) },
          { signal },
        )
        if (signal.aborted) return
        const nextResults: TeamRequirementResult[] = response.results.map((row, index) => ({
          requirement: applied[index],
          eligible: row.eligible,
          assigned: row.assigned,
          labels: row.labels ?? [],
          shortfall: row.shortfall,
          canFill: row.can_fill,
          error: row.error,
        }))
        setResults({
          canForm: response.can_form,
          results: nextResults,
        })
      } catch (err: unknown) {
        if (signal.aborted || isAbortError(err)) return
        setResults(null)
        setError(err instanceof Error ? err.message : 'Failed to search team')
      } finally {
        if (!signal.aborted) setLoading(false)
      }
    }

    void run()
    return () => controller.abort()
  }, [applied, refreshKey])

  function updateRequirement(id: string, patch: Partial<Omit<TeamRequirement, 'id'>>) {
    setRequirements((rows) => rows.map((row) => (row.id === id ? { ...row, ...patch } : row)))
  }

  function handleAdd() {
    setRequirements((rows) => [...rows, createTeamRequirement()])
  }

  function handleRemove(id: string) {
    setRequirements((rows) => (rows.length <= 1 ? rows : rows.filter((row) => row.id !== id)))
  }

  function handleSearch(event: FormEvent) {
    event.preventDefault()
    const missing = requirements.some((row) => !row.afsc.trim())
    if (missing) {
      setError('Each requirement needs an AFSC.')
      setResults(null)
      return
    }
    setError(null)
    setApplied(
      requirements.map((row) => ({
        ...row,
        afsc: row.afsc.trim(),
      })),
    )
  }

  function handleClear() {
    setRequirements(emptyTeamRequirements())
    setApplied(null)
    setResults(null)
    setError(null)
    setLoading(false)
  }

  return (
    <section className="panel">
      <h2>Team search</h2>
      <p className="muted">
        Specify the AFSC and type needed for each role, then search to see whether the team can be
        formed. Each person fills at most one seat across requirements.
      </p>

      <form className="team-search-form" onSubmit={handleSearch}>
        <div className="team-requirements">
          {requirements.map((row) => (
            <div key={row.id} className="filters team-requirement-row">
              <label>
                AFSC
                <input
                  type="text"
                  value={row.afsc}
                  required
                  onChange={(e) => updateRequirement(row.id, { afsc: e.target.value })}
                  placeholder="e.g. 1A1X2"
                />
              </label>
              <label>
                Type
                <select
                  value={row.personnel_type}
                  onChange={(e) =>
                    updateRequirement(row.id, {
                      personnel_type: e.target.value as PersonnelType | '',
                    })
                  }
                >
                  <option value="">All</option>
                  <option value="enlisted">Enlisted</option>
                  <option value="officer">Officer</option>
                </select>
              </label>
              <label>
                Needed
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={row.needed}
                  onChange={(e) => {
                    const value = Number.parseInt(e.target.value, 10)
                    updateRequirement(row.id, {
                      needed: Number.isFinite(value) && value >= 1 ? value : 1,
                    })
                  }}
                />
              </label>
              <div className="team-row-remove">
                <span className="team-row-remove-spacer" aria-hidden="true">
                  &nbsp;
                </span>
                <button
                  type="button"
                  className="team-row-remove-btn"
                  aria-label="Remove requirement"
                  disabled={requirements.length <= 1}
                  onClick={() => handleRemove(row.id)}
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="team-add-row">
          <button type="button" className="secondary" onClick={handleAdd}>
            + Add requirement
          </button>
        </div>

        <div className="filters team-search-actions-row">
          <div className="filter-actions">
            <button type="submit" className="primary" disabled={loading}>
              Search team
            </button>
            <button type="button" className="secondary" onClick={handleClear}>
              Clear
            </button>
          </div>
        </div>
      </form>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Checking eligibility…</p>}

      {!loading && results && (
        <div className="team-results">
          <p
            className={
              results.canForm ? 'team-verdict team-verdict-ok' : 'team-verdict team-verdict-short'
            }
          >
            {results.canForm ? 'Team can be formed' : 'Cannot form team'}
          </p>

          <ul className="team-result-list">
            {results.results.map(
              ({ requirement, eligible, assigned, labels, shortfall, canFill, error: rowError }) => (
                <li key={requirement.id} className="team-result-item">
                  <div className="team-result-main">
                    <span className="team-result-label">{formatRequirementLabel(requirement)}</span>
                    <span className={canFill ? 'team-result-status ok' : 'team-result-status short'}>
                      {rowError
                        ? rowError
                        : canFill
                          ? `${assigned} filled · ${eligible} matching · needed ${requirement.needed}`
                          : `${assigned} of ${requirement.needed} filled · ${eligible} matching · short by ${shortfall}`}
                    </span>
                  </div>
                  {labels.length > 0 && (
                    <div className="label-pills">
                      {labels.map((label) => (
                        <span key={label} className="label-pill label-pill-active">
                          {label}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ),
            )}
          </ul>
        </div>
      )}
    </section>
  )
}
