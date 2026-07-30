import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react'
import { commitRoster, discardRoster, previewRoster } from '../api'
import type { PreviewOut, PreviewRowOut } from '../types'

interface UploadModalProps {
  onClose: () => void
  onRosterChanged: () => void
}

type Phase = 'pick' | 'review'

const PAGE_SIZE = 25

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function isVisible(el: HTMLElement): boolean {
  return el.getClientRects().length > 0
}

function getFocusable(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter((el) => {
    if (el.closest('[inert], [aria-hidden="true"]')) return false
    return isVisible(el)
  })
}

function focusFirst(root: HTMLElement | null) {
  if (!root) return
  const focusable = getFocusable(root)
  focusable[0]?.focus()
}

export function UploadModal({ onClose, onRosterChanged }: UploadModalProps) {
  const [phase, setPhase] = useState<Phase>('pick')
  const [preview, setPreview] = useState<PreviewOut | null>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [committing, setCommitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resultTab, setResultTab] = useState<'success' | 'failure'>('success')
  const [page, setPage] = useState(0)
  const [confirmClose, setConfirmClose] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const previewIdRef = useRef<string | null>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const confirmCardRef = useRef<HTMLDivElement>(null)
  const previouslyFocused = useRef<HTMLElement | null>(null)
  const confirmCloseRef = useRef(confirmClose)
  const wasConfirming = useRef(false)

  confirmCloseRef.current = confirmClose

  const discardPreview = useCallback(async () => {
    const id = previewIdRef.current
    previewIdRef.current = null
    if (!id) return
    try {
      await discardRoster(id)
    } catch {
      // no-op
    }
  }, [])

  const hasUnsavedPreview = phase === 'review' && preview != null

  const closeNow = useCallback(async () => {
    setConfirmClose(false)
    await discardPreview()
    onClose()
  }, [discardPreview, onClose])

  const requestClose = useCallback(() => {
    if (loading || committing) return
    if (hasUnsavedPreview) {
      setConfirmClose(true)
      return
    }
    void closeNow()
  }, [closeNow, committing, hasUnsavedPreview, loading])

  useEffect(() => {
    previouslyFocused.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null

    const panel = panelRef.current
    const frame = window.requestAnimationFrame(() => focusFirst(panel))

    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Tab' || !panelRef.current) return

      const trapRoot = confirmCloseRef.current
        ? confirmCardRef.current ?? panelRef.current
        : panelRef.current
      const focusable = getFocusable(trapRoot)
      if (focusable.length === 0) {
        event.preventDefault()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement

      if (event.shiftKey) {
        if (active === first || !trapRoot.contains(active)) {
          event.preventDefault()
          last.focus()
        }
      } else if (active === last || !trapRoot.contains(active)) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      window.cancelAnimationFrame(frame)
      document.removeEventListener('keydown', onKeyDown)
      previouslyFocused.current?.focus?.()
    }
  }, [])

  useEffect(() => {
    if (confirmClose) {
      wasConfirming.current = true
      const frame = window.requestAnimationFrame(() => focusFirst(confirmCardRef.current))
      return () => window.cancelAnimationFrame(frame)
    }
    if (wasConfirming.current) {
      wasConfirming.current = false
      const frame = window.requestAnimationFrame(() => focusFirst(panelRef.current))
      return () => window.cancelAnimationFrame(frame)
    }
  }, [confirmClose])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (confirmClose) {
          setConfirmClose(false)
        } else {
          requestClose()
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [confirmClose, requestClose])

  async function parseFile(file: File) {
    if (!file.name.toLowerCase().match(/\.(xlsx|xlsm)$/)) {
      setError('Choose an .xlsx or .xlsm workbook')
      return
    }
    setLoading(true)
    setError(null)
    await discardPreview()
    try {
      const result = await previewRoster(file)
      previewIdRef.current = result.upload_id
      setPreview(result)
      setResultTab(result.failures.length && !result.successes.length ? 'failure' : 'success')
      setPage(0)
      setPhase('review')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to parse workbook')
      setPhase('pick')
      setPreview(null)
    } finally {
      setLoading(false)
    }
  }

  function onFileInput(files: FileList | null) {
    const file = files?.[0]
    if (file) void parseFile(file)
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    onFileInput(event.dataTransfer.files)
  }

  async function handleApprove() {
    if (!preview?.can_commit) return
    setCommitting(true)
    setError(null)
    try {
      await commitRoster(preview.upload_id)
      previewIdRef.current = null
      onRosterChanged()
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to apply roster')
    } finally {
      setCommitting(false)
    }
  }

  async function handleChooseAnother() {
    await discardPreview()
    setPreview(null)
    setPhase('pick')
    setPage(0)
    setError(null)
    setConfirmClose(false)
    if (inputRef.current) inputRef.current.value = ''
  }

  const allRows: PreviewRowOut[] =
    preview == null ? [] : resultTab === 'success' ? preview.successes : preview.failures

  const pageCount = Math.max(1, Math.ceil(allRows.length / PAGE_SIZE))
  const safePage = Math.min(page, pageCount - 1)
  const pageRows = useMemo(() => {
    const start = safePage * PAGE_SIZE
    return allRows.slice(start, start + PAGE_SIZE)
  }, [allRows, safePage])

  const from = allRows.length === 0 ? 0 : safePage * PAGE_SIZE + 1
  const to = Math.min(allRows.length, (safePage + 1) * PAGE_SIZE)

  function switchTab(tab: 'success' | 'failure') {
    setResultTab(tab)
    setPage(0)
  }

  return (
    <div className="modal-backdrop" onClick={requestClose} role="presentation">
      <div
        ref={panelRef}
        className="modal-panel upload-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div inert={confirmClose ? true : undefined}>
          <div className="modal-header">
            <h2 id="upload-title">Upload roster</h2>
            <button type="button" className="secondary" onClick={requestClose}>
              Close
            </button>
          </div>

          {phase === 'pick' && (
            <>
              <p className="muted">
                Drop an Excel workbook here, or choose a file. Nothing is applied until you review
                and approve.
              </p>

              <div
                className={`upload-dropzone${dragging ? ' is-dragging' : ''}${loading ? ' is-loading' : ''}`}
                onDragEnter={(e) => {
                  e.preventDefault()
                  setDragging(true)
                }}
                onDragOver={(e) => e.preventDefault()}
                onDragLeave={(e) => {
                  e.preventDefault()
                  setDragging(false)
                }}
                onDrop={onDrop}
                onClick={() => !loading && inputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    inputRef.current?.click()
                  }
                }}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept=".xlsx,.xlsm"
                  hidden
                  onChange={(e) => onFileInput(e.target.files)}
                />
                <p className="upload-dropzone-title">
                  {loading ? 'Parsing workbook…' : 'Drag & drop spreadsheet'}
                </p>
                <p className="muted upload-dropzone-hint">
                  {loading ? 'Validating AFSCs and rows' : 'or click to choose an .xlsx file'}
                </p>
              </div>
            </>
          )}

          {phase === 'review' && preview && (
            <div className="upload-modal-review">
              <p className="muted">
                <strong>{preview.filename}</strong>
              </p>

              <div className="upload-result-tabs">
                <button
                  type="button"
                  className={`upload-result-tab${resultTab === 'success' ? ' active' : ''}`}
                  onClick={() => switchTab('success')}
                >
                  Success ({preview.successes.length})
                </button>
                <button
                  type="button"
                  className={`upload-result-tab${resultTab === 'failure' ? ' active' : ''}`}
                  onClick={() => switchTab('failure')}
                >
                  Failures ({preview.failures.length})
                </button>
              </div>

              <div className="pagination upload-pagination">
                <p className="muted count">
                  {allRows.length === 0
                    ? 'No rows'
                    : `Showing ${from}–${to} of ${allRows.length}`}
                </p>
                <div className="filter-actions">
                  <button
                    type="button"
                    className="secondary"
                    disabled={safePage <= 0 || allRows.length === 0}
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                  >
                    Previous
                  </button>
                  <span className="muted page-indicator">
                    Page {allRows.length === 0 ? 0 : safePage + 1} /{' '}
                    {allRows.length === 0 ? 0 : pageCount}
                  </span>
                  <button
                    type="button"
                    className="secondary"
                    disabled={safePage + 1 >= pageCount || allRows.length === 0}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>

              <div className="table-wrap upload-preview-table">
                <table>
                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>DODID</th>
                      <th>Name</th>
                      <th>AFSC</th>
                      {resultTab === 'failure' && <th>Reason</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {pageRows.length === 0 ? (
                      <tr>
                        <td colSpan={resultTab === 'failure' ? 5 : 4} className="muted">
                          No {resultTab === 'success' ? 'successful' : 'failed'} rows.
                        </td>
                      </tr>
                    ) : (
                      pageRows.map((row, idx) => (
                        <tr key={`${row.row}-${row.dodid}-${safePage}-${idx}`}>
                          <td>{row.row ?? '—'}</td>
                          <td>{row.dodid ?? '—'}</td>
                          <td>{row.display_name ?? '—'}</td>
                          <td>
                            {row.normalized_afsc ? (
                              <code>{row.normalized_afsc}</code>
                            ) : row.afsc ? (
                              <code>{row.afsc}</code>
                            ) : (
                              '—'
                            )}
                          </td>
                          {resultTab === 'failure' && <td>{row.reason ?? '—'}</td>}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <div className="pagination upload-pagination">
                <p className="muted count">
                  {allRows.length === 0
                    ? 'No rows'
                    : `Showing ${from}–${to} of ${allRows.length}`}
                </p>
                <div className="filter-actions">
                  <button
                    type="button"
                    className="secondary"
                    disabled={safePage <= 0 || allRows.length === 0}
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                  >
                    Previous
                  </button>
                  <span className="muted page-indicator">
                    Page {allRows.length === 0 ? 0 : safePage + 1} /{' '}
                    {allRows.length === 0 ? 0 : pageCount}
                  </span>
                  <button
                    type="button"
                    className="secondary"
                    disabled={safePage + 1 >= pageCount || allRows.length === 0}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>

              <div className="upload-review-actions">
                <button type="button" className="secondary" onClick={() => void handleChooseAnother()}>
                  Choose another file
                </button>
                <button
                  type="button"
                  className="primary"
                  disabled={!preview.can_commit || committing}
                  onClick={() => void handleApprove()}
                >
                  {committing
                    ? 'Applying…'
                    : preview.can_commit
                      ? `Approve & apply (${preview.accepted_rows})`
                      : 'Nothing to apply'}
                </button>
              </div>
            </div>
          )}

          {error && <p className="error">{error}</p>}
        </div>

        {confirmClose && (
          <div
            className="confirm-overlay"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-close-title"
            aria-describedby="confirm-close-desc"
          >
            <div className="confirm-card" ref={confirmCardRef}>
              <h3 id="confirm-close-title">Discard this upload?</h3>
              <p id="confirm-close-desc" className="muted">
                Your parsed results won’t be applied. This can’t be undone.
              </p>
              <div className="confirm-actions">
                <button type="button" className="secondary" onClick={() => setConfirmClose(false)}>
                  Keep reviewing
                </button>
                <button type="button" className="primary" onClick={() => void closeNow()}>
                  Discard & close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
