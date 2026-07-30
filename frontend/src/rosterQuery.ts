import type { MemberFilters, PersonnelType } from './types'

export const PAGE_SIZE = 25

export interface RosterFilters {
  name: string
  dodid: string
  afsc: string
  personnel_type: PersonnelType | ''
}

export interface MemberSelectContext {
  searchLabels: string[]
  filters: RosterFilters
  page: number
}

export function emptyRosterFilters(): RosterFilters {
  return { name: '', dodid: '', afsc: '', personnel_type: '' }
}

export function filtersHaveSearch(filters: RosterFilters): boolean {
  return Boolean(
    filters.name.trim() ||
      filters.dodid.trim() ||
      filters.afsc.trim() ||
      filters.personnel_type,
  )
}

export function toMemberFilters(
  filters: RosterFilters,
  page: number,
  fallbackAfsc?: string | null,
): MemberFilters {
  const hasSearch = filtersHaveSearch(filters)
  return {
    name: filters.name.trim() || undefined,
    dodid: filters.dodid.trim() || undefined,
    afsc: filters.afsc.trim() || (!hasSearch ? fallbackAfsc || undefined : undefined),
    personnel_type: filters.personnel_type || undefined,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  }
}
