import { useCallback, useEffect, useState, Fragment } from 'react'
import { clearRoster, isAbortError, listUploads } from '../api'
import type { UploadOut, UploadStatus } from '../types'

interface UploadHistoryPanelProps {
  refreshKey: number
  onBack: () => void
  onRosterCleared: () => void
}

function formatUploadedAt(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function statusClass(status: UploadStatus): string {
  if (status === 'succeeded') return 'status-pill status-succeeded'
  if (status === 'failed') return 'status-pill status-failed'
  return 'status-pill status-pending'
}

export function UploadHistoryPanel({
  refreshKey,
  onBack,
  onRosterCleared,
}: UploadHistoryPanelProps) {
  const [uploads, setUploads] = useState<UploadOut[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [confirmClear, setConfirmClear] = useState(false)
  const [clearing, setClearing] = useState(false)

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError(null)
    try {
      const next = await listUploads({ signal })
      if (signal?.aborted) return
      setUploads(next)
    } catch (err: unknown) {
      if (signal?.aborted || isAbortError(err)) return
      setUploads([])
      setError(err instanceof Error ? err.message : 'Failed to load upload history')
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [load, refreshKey])

  async function handleClearRoster() {
    setClearing(true)
    setError(null)
    try {
      await clearRoster()
      setConfirmClear(false)
      onRosterCleared()
      await load()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to clear roster')
    } finally {
      setClearing(false)
    }
  }

  return (
    <section className="panel">
      <button type="button" className="secondary back-btn" onClick={onBack}>
        ← Back to roster
      </button>
      <div className="panel-heading-row">
        <div>
          <h2>Upload history</h2>
          <p className="muted">Results of past roster uploads.</p>
        </div>
        <button
          type="button"
          className="danger"
          disabled={clearing}
          onClick={() => setConfirmClear(true)}
        >
          Clear roster
        </button>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading uploads…</p>}

      {!loading && !error && uploads.length === 0 && (
        <p className="muted">No uploads yet.</p>
      )}

      {uploads.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Uploaded</th>
                <th>Status</th>
                <th>Total</th>
                <th>Accepted</th>
                <th>Rejected</th>
                <th>Ruleset</th>
                <th>Active</th>
                <th>Issues</th>
              </tr>
            </thead>
            <tbody>
              {uploads.map((upload) => {
                const expanded = expandedId === upload.upload_id
                return (
                  <Fragment key={upload.upload_id}>
                    <tr>
                      <td>{upload.filename}</td>
                      <td>{formatUploadedAt(upload.uploaded_at)}</td>
                      <td>
                        <span className={statusClass(upload.status)}>{upload.status}</span>
                      </td>
                      <td>{upload.total_rows}</td>
                      <td>{upload.accepted_rows}</td>
                      <td>{upload.rejected_rows}</td>
                      <td>
                        <code>{upload.ruleset_version}</code>
                      </td>
                      <td>
                        {upload.is_active ? (
                          <span className="status-pill status-active">Active</span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>
                        {upload.issues.length === 0 ? (
                          '—'
                        ) : (
                          <button
                            type="button"
                            className="secondary"
                            onClick={() =>
                              setExpandedId(expanded ? null : upload.upload_id)
                            }
                          >
                            {expanded ? 'Hide' : `${upload.issues.length}`}
                          </button>
                        )}
                      </td>
                    </tr>
                    {expanded && (
                      <tr>
                        <td colSpan={9}>
                          <ul className="upload-issue-list">
                            {upload.issues.map((issue, index) => (
                              <li key={`${upload.upload_id}-issue-${index}`}>
                                {issue.row != null ? `Row ${issue.row}: ` : ''}
                                {issue.field ? `${issue.field} — ` : ''}
                                {issue.reason}
                                {issue.value ? ` (${issue.value})` : ''}
                              </li>
                            ))}
                          </ul>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {confirmClear && (
        <div
          className="confirm-overlay panel-confirm-overlay"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="confirm-clear-title"
          aria-describedby="confirm-clear-desc"
        >
          <div className="confirm-card">
            <h3 id="confirm-clear-title">Clear entire roster?</h3>
            <p id="confirm-clear-desc" className="muted">
              This deletes every service member from the database. Upload history is kept.
              This can’t be undone.
            </p>
            <div className="confirm-actions">
              <button
                type="button"
                className="secondary"
                disabled={clearing}
                onClick={() => setConfirmClear(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger"
                disabled={clearing}
                onClick={() => void handleClearRoster()}
              >
                {clearing ? 'Clearing…' : 'Clear roster'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
