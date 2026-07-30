import type { PersonnelType, TeamCheckRequirement } from './types'

export interface TeamRequirement {
  id: string
  afsc: string
  personnel_type: PersonnelType | ''
  needed: number
}

export interface TeamRequirementResult {
  requirement: TeamRequirement
  eligible: number
  assigned: number
  labels: string[]
  shortfall: number
  canFill: boolean
  error: string | null
}

export interface TeamSearchResults {
  canForm: boolean
  results: TeamRequirementResult[]
}

let nextRequirementId = 1

export function createTeamRequirement(
  partial?: Partial<Omit<TeamRequirement, 'id'>>,
): TeamRequirement {
  return {
    id: `req-${nextRequirementId++}`,
    afsc: partial?.afsc ?? '',
    personnel_type: partial?.personnel_type ?? '',
    needed: partial?.needed ?? 1,
  }
}

export function emptyTeamRequirements(): TeamRequirement[] {
  return [createTeamRequirement()]
}

export function requirementToCheckPayload(requirement: TeamRequirement): TeamCheckRequirement {
  return {
    afsc: requirement.afsc.trim(),
    personnel_type: requirement.personnel_type || null,
    needed: requirement.needed,
  }
}

export function formatRequirementLabel(requirement: TeamRequirement): string {
  const parts = [requirement.afsc.trim()]
  if (requirement.personnel_type) {
    parts.push(requirement.personnel_type === 'enlisted' ? 'Enlisted' : 'Officer')
  }
  return parts.join(' · ')
}
