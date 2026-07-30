export type UploadStatus = 'pending' | 'succeeded' | 'failed'
export type PersonnelType = 'enlisted' | 'officer'
export type IssueSeverity = 'error' | 'warning'

export interface IssueOut {
  row: number | null
  field: string | null
  value: string | null
  reason: string
  severity: IssueSeverity
}

export interface UploadOut {
  upload_id: string
  filename: string
  uploaded_at: string | null
  status: UploadStatus
  total_rows: number
  accepted_rows: number
  rejected_rows: number
  ruleset_version: string
  is_active: boolean
  issues: IssueOut[]
}

export interface ClearRosterOut {
  deleted_members: number
}

export interface PreviewRowOut {
  row: number | null
  status: 'success' | 'failure'
  dodid: string | null
  display_name: string | null
  afsc: string | null
  normalized_afsc: string | null
  personnel_type: PersonnelType | null
  reason: string | null
  severity: IssueSeverity | null
}

export interface PreviewOut {
  upload_id: string
  filename: string
  ruleset_version: string
  total_rows: number
  accepted_rows: number
  rejected_rows: number
  can_commit: boolean
  successes: PreviewRowOut[]
  failures: PreviewRowOut[]
}

export interface MemberOut {
  id: string
  dodid: string
  display_name: string
  rank: string | null
  personnel_type: PersonnelType | null
  afsc: string
  normalized_afsc: string
  afsc_label: string | null
  afsc_labels: string[]
  afsc_family: string | null
  afsc_level: string | null
  afsc_specialization: string | null
  created_at: string | null
}

export interface MembersPage {
  members: MemberOut[]
  total: number
  limit: number
  offset: number
}

export interface SearchLabelsOut {
  pattern: string
  labels: string[]
}

export interface TeamCheckRequirement {
  afsc: string
  personnel_type?: PersonnelType | null
  needed: number
}

export interface TeamCheckRequest {
  requirements: TeamCheckRequirement[]
}

export interface TeamCheckResult {
  afsc: string
  personnel_type: PersonnelType | null
  needed: number
  eligible: number
  assigned: number
  shortfall: number
  can_fill: boolean
  labels: string[]
  error: string | null
}

export interface TeamCheckResponse {
  can_form: boolean
  results: TeamCheckResult[]
}

export interface CatalogCodeLabel {
  code: string
  label: string
}

export interface CatalogFamily {
  pattern: string
  personnel_type: PersonnelType
  career_group: string
  career_field: string
  title: string
  wildcard_role: string
  levels: Record<string, string>
  suffixes: Record<string, string>
  subdivision: string | null
  subdivision_title: string | null
  specialty_char: string | null
  utilization: string | null
}

export interface CatalogOut {
  version: string
  sources: string[]
  career_groups: CatalogCodeLabel[]
  career_fields: CatalogCodeLabel[]
  families: CatalogFamily[]
}

export interface MemberFilters {
  name?: string
  dodid?: string
  afsc?: string
  personnel_type?: PersonnelType | ''
  limit?: number
  offset?: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  reply: string
  tool_traces: unknown[]
}
