import { useEffect, useMemo, useRef, useState } from 'react'
import { getAfscCatalog } from '../api'
import {
  buildSlotDefs,
  patternFromSlots,
  pruneSlots,
  slotsFromPattern,
  type SlotValues,
} from '../afscSlots'
import type { CatalogOut, PersonnelType } from '../types'

interface AfscDetailedSearchProps {
  afsc: string
  personnelType: PersonnelType | ''
  onAfscChange: (value: string) => void
}

function sameSlots(a: SlotValues, b: SlotValues): boolean {
  return a.every((value, index) => value === b[index])
}

function sanitizeSlots(
  catalog: CatalogOut,
  slots: SlotValues,
  personnelType: PersonnelType | '',
): SlotValues {
  const defs = buildSlotDefs(catalog, slots, personnelType)
  const next = [...slots] as SlotValues
  for (const def of defs) {
    const value = next[def.index]
    if (!value) continue
    if (def.disabled) {
      next[def.index] = ''
      continue
    }
    const allowed =
      (def.allowAny && value === 'X') || def.options.some((o) => o.value === value)
    if (!allowed) next[def.index] = ''
  }
  return next
}

export function AfscDetailedSearch({
  afsc,
  personnelType,
  onAfscChange,
}: AfscDetailedSearchProps) {
  const [open, setOpen] = useState(false)
  const [catalog, setCatalog] = useState<CatalogOut | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [slots, setSlots] = useState<SlotValues>(() => slotsFromPattern(afsc))
  const lastEmitted = useRef(afsc.trim().toUpperCase())

  useEffect(() => {
    const controller = new AbortController()
    void getAfscCatalog({ signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setCatalog(data)
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setLoadError(err instanceof Error ? err.message : 'Failed to load AFSC catalog')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const normalized = afsc.trim().toUpperCase()
    if (normalized === lastEmitted.current) return
    lastEmitted.current = normalized
    setSlots(slotsFromPattern(normalized))
  }, [afsc])

  useEffect(() => {
    if (!catalog) return
    setSlots((prev) => {
      const cleaned = sanitizeSlots(catalog, prev, personnelType)
      return sameSlots(prev, cleaned) ? prev : cleaned
    })
  }, [personnelType, catalog])

  useEffect(() => {
    const pattern = patternFromSlots(slots)
    if (pattern === lastEmitted.current) return
    lastEmitted.current = pattern
    onAfscChange(pattern)
  }, [slots, onAfscChange])

  const slotDefs = useMemo(() => {
    if (!catalog) return []
    return buildSlotDefs(catalog, slots, personnelType)
  }, [catalog, slots, personnelType])

  function handleSlotChange(index: number, value: string) {
    if (!catalog) return
    const pruned = pruneSlots(slots, index)
    pruned[index] = value
    const cleaned = sanitizeSlots(catalog, pruned, personnelType)
    const pattern = patternFromSlots(cleaned)
    lastEmitted.current = pattern
    setSlots(cleaned)
    onAfscChange(pattern)
  }

  const preview = patternFromSlots(slots)

  return (
    <div className="detailed-search">
      <button
        type="button"
        className="detailed-search-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="detailed-search-chevron" aria-hidden>
          {open ? '▾' : '▸'}
        </span>
        Detailed AFSC search
        {preview && <code className="detailed-search-preview">{preview}</code>}
      </button>

      {open && (
        <div className="detailed-search-body">
          {loadError && <p className="error">{loadError}</p>}
          {!catalog && !loadError && <p className="muted">Loading catalog…</p>}

          {catalog && (
            <div className="detailed-search-slots">
              {slotDefs.map((def) => (
                <label
                  key={def.index}
                  className={def.disabled ? 'slot-disabled' : undefined}
                  title={def.reason ?? undefined}
                >
                  {def.label}
                  <select
                    value={slots[def.index]}
                    disabled={def.disabled}
                    onChange={(e) => handleSlotChange(def.index, e.target.value)}
                  >
                    <option value="">—</option>
                    {def.allowAny && <option value="X">Any (X)</option>}
                    {def.options.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
