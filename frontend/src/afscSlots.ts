import type { CatalogFamily, CatalogOut, PersonnelType } from './types'

export const SLOT_COUNT = 6
export type AfscMode = 'unknown' | PersonnelType
export type SlotValues = [string, string, string, string, string, string]

export interface SlotOption {
  value: string
  label: string
}

export interface SlotDef {
  index: number
  label: string
  options: SlotOption[]
  disabled: boolean
  reason: string | null
  allowAny: boolean
}

export function emptySlots(): SlotValues {
  return ['', '', '', '', '', '']
}

export function slotsFromPattern(pattern: string): SlotValues {
  const normalized = pattern.trim().toUpperCase()
  const slots = emptySlots()
  for (let i = 0; i < Math.min(SLOT_COUNT, normalized.length); i += 1) {
    const ch = normalized[i]
    slots[i] = ch === 'X' && i >= 2 ? 'X' : ch === 'X' ? '' : ch
  }
  return slots
}

export function patternFromSlots(slots: SlotValues): string {
  let last = -1
  for (let i = 0; i < slots.length; i += 1) {
    if (slots[i]) last = i
  }
  if (last < 0) return ''

  const chars: string[] = []
  for (let i = 0; i <= last; i += 1) {
    const value = slots[i]
    if (!value) {
      if (i < 2) return chars.join('')
      chars.push('X')
    } else if (value === 'X') {
      if (i < 2) return chars.join('')
      chars.push('X')
    } else {
      chars.push(value)
    }
  }
  return chars.join('')
}

export function detectMode(
  slots: SlotValues,
  personnelType: PersonnelType | '',
): AfscMode {
  if (personnelType) return personnelType
  const second = slots[1]
  if (second && /[A-Z]/.test(second)) return 'enlisted'
  if (second && /\d/.test(second)) return 'officer'
  return 'unknown'
}

function familyMatchesPrefix(family: CatalogFamily, slots: SlotValues, mode: AfscMode): boolean {
  if (mode !== 'unknown' && family.personnel_type !== mode) return false
  if (slots[0] && family.career_group !== slots[0]) return false
  if (slots[1] && family.career_field[1] !== slots[1]) return false

  if (family.personnel_type === 'enlisted') {
    if (slots[2] && family.subdivision && family.subdivision !== slots[2]) return false
    if (slots[4] && slots[4] !== 'X' && family.specialty_char && family.specialty_char !== slots[4]) {
      return false
    }
  }

  if (family.personnel_type === 'officer') {
    if (slots[2] && slots[2] !== 'X' && family.utilization && family.utilization !== slots[2]) {
      return false
    }
  }

  return true
}

function uniqueOptions(
  entries: Iterable<[string, string]>,
): SlotOption[] {
  const map = new Map<string, string>()
  for (const [code, label] of entries) {
    if (!map.has(code)) map.set(code, label)
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([value, label]) => ({ value, label: `${value} — ${label}` }))
}

function fieldLabel(catalog: CatalogOut, code: string): string {
  return catalog.career_fields.find((f) => f.code === code)?.label ?? code
}

function groupLabel(catalog: CatalogOut, code: string): string {
  return catalog.career_groups.find((g) => g.code === code)?.label ?? code
}

export function buildSlotDefs(
  catalog: CatalogOut,
  slots: SlotValues,
  personnelType: PersonnelType | '',
): SlotDef[] {
  const mode = detectMode(slots, personnelType)
  const families = catalog.families.filter((f) => familyMatchesPrefix(f, slots, mode))

  const hasGroup = Boolean(slots[0])
  const hasField = Boolean(slots[1])
  const hasThird = Boolean(slots[2])
  const prefixReady = hasGroup && hasField

  const officerLocked = mode === 'officer' || personnelType === 'officer'

  const p0Options = uniqueOptions(
    (personnelType
      ? catalog.families.filter((f) => f.personnel_type === personnelType)
      : catalog.families
    ).map((f) => [f.career_group, groupLabel(catalog, f.career_group)]),
  )

  const p1Families = catalog.families.filter((f) => {
    if (personnelType && f.personnel_type !== personnelType) return false
    if (slots[0] && f.career_group !== slots[0]) return false
    return true
  })
  const p1Options = uniqueOptions(
    p1Families.map((f) => {
      const ch = f.career_field[1] ?? ''
      const label = fieldLabel(catalog, f.career_field)
      return [ch, label]
    }),
  )

  let p2Label = 'Field / util.'
  let p2Options: SlotOption[] = []
  let p2Disabled = !prefixReady
  let p2Reason: string | null = null
  let p2AllowAny = false

  if (!hasGroup || !hasField) {
    p2Disabled = true
    p2Reason = 'Select career group and field first'
  } else if (mode === 'unknown') {
    p2Disabled = true
    p2Reason = 'Career field must identify enlisted or officer'
  } else if (mode === 'enlisted') {
    p2Label = 'Subdivision'
    p2Options = uniqueOptions(
      families
        .filter((f) => f.personnel_type === 'enlisted' && f.subdivision)
        .map((f) => [f.subdivision!, f.subdivision_title || f.title]),
    )
    p2AllowAny = false
  } else {
    p2Label = 'Utilization'
    p2Options = uniqueOptions(
      families
        .filter((f) => f.personnel_type === 'officer' && f.utilization)
        .map((f) => [f.utilization!, f.title]),
    )
    p2AllowAny = true
  }

  let p3Label = 'Level'
  let p3Options: SlotOption[] = []
  let p3Disabled = !prefixReady
  let p3Reason: string | null = prefixReady ? null : 'Select career group and field first'
  const p3AllowAny = true

  if (prefixReady && mode !== 'unknown') {
    p3Label = mode === 'enlisted' ? 'Skill level' : 'Qualification'
    const levelEntries: [string, string][] = []
    for (const f of families) {
      if (f.personnel_type !== mode) continue
      for (const [code, label] of Object.entries(f.levels)) {
        levelEntries.push([code, label])
      }
    }
    p3Options = uniqueOptions(levelEntries)
  } else if (prefixReady && mode === 'unknown') {
    p3Disabled = true
    p3Reason = 'Career field must identify enlisted or officer'
  }

  let p4Label = 'Specialty / shred'
  let p4Options: SlotOption[] = []
  let p4Disabled = true
  let p4Reason: string | null = 'Select preceding AFSC positions first'
  let p4AllowAny = false

  if (!prefixReady) {
    p4Disabled = true
    p4Reason = 'Select career group and field first'
  } else if (mode === 'unknown') {
    p4Disabled = true
    p4Reason = 'Career field must identify enlisted or officer'
  } else if (mode === 'enlisted') {
    p4Label = 'Specialty'
    p4AllowAny = true
    p4Disabled = !hasThird
    p4Reason = hasThird ? null : 'Select subdivision first'
    if (hasThird) {
      p4Options = uniqueOptions(
        families
          .filter((f) => f.personnel_type === 'enlisted' && f.specialty_char)
          .map((f) => [f.specialty_char!, f.title]),
      )
    }
  } else {
    p4Label = 'Suffix'
    p4AllowAny = false
    p4Disabled = false
    p4Reason = null
    p4Options = uniqueOptions(
      families
        .filter((f) => f.personnel_type === 'officer')
        .flatMap((f) => Object.entries(f.suffixes)),
    )
  }

  let p5Label = 'Suffix'
  let p5Options: SlotOption[] = []
  let p5Disabled = true
  let p5Reason: string | null = null
  const p5AllowAny = false

  if (officerLocked) {
    p5Disabled = true
    p5Reason = 'Officer AFSCs have no 6th character'
    p5Label = 'Suffix (n/a)'
  } else if (!prefixReady || mode === 'unknown') {
    p5Disabled = true
    p5Reason = 'Available for enlisted shredouts only'
  } else {
    p5Label = 'Suffix'
    const specialtySet = slots[4] && slots[4] !== 'X'
    p5Disabled = !specialtySet
    p5Reason = specialtySet ? null : 'Select specialty first'
    if (specialtySet) {
      p5Options = uniqueOptions(
        families
          .filter((f) => f.personnel_type === 'enlisted')
          .flatMap((f) => Object.entries(f.suffixes)),
      )
    }
  }

  return [
    {
      index: 0,
      label: 'Career group',
      options: p0Options,
      disabled: false,
      reason: null,
      allowAny: false,
    },
    {
      index: 1,
      label: 'Career field',
      options: p1Options,
      disabled: !hasGroup,
      reason: hasGroup ? null : 'Select career group first',
      allowAny: false,
    },
    {
      index: 2,
      label: p2Label,
      options: p2Options,
      disabled: p2Disabled,
      reason: p2Reason,
      allowAny: p2AllowAny,
    },
    {
      index: 3,
      label: p3Label,
      options: p3Options,
      disabled: p3Disabled,
      reason: p3Reason,
      allowAny: p3AllowAny,
    },
    {
      index: 4,
      label: p4Label,
      options: p4Options,
      disabled: p4Disabled,
      reason: p4Reason,
      allowAny: p4AllowAny,
    },
    {
      index: 5,
      label: p5Label,
      options: p5Options,
      disabled: p5Disabled,
      reason: p5Reason,
      allowAny: p5AllowAny,
    },
  ]
}

export function pruneSlots(slots: SlotValues, changedIndex: number): SlotValues {
  const next = [...slots] as SlotValues
  for (let i = changedIndex + 1; i < SLOT_COUNT; i += 1) {
    next[i] = ''
  }
  return next
}
