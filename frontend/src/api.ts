import type {
  CatalogOut,
  ChatMessage,
  ChatResponse,
  ClearRosterOut,
  MemberFilters,
  MembersPage,
  PreviewOut,
  SearchLabelsOut,
  TeamCheckRequest,
  TeamCheckResponse,
  UploadOut,
} from './types'

const API_BASE = String(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

async function parseError(response: Response): Promise<never> {
  let detail = `Request failed (${response.status})`
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') {
      detail = body.detail
    } else if (body.detail != null) {
      detail = JSON.stringify(body.detail)
    }
  } catch {
    // no-op
  }
  throw new Error(detail)
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    await parseError(response)
  }
  if (response.status === 204) {
    return null as T
  }
  return (await response.json()) as T
}

export function listUploads(init?: RequestInit): Promise<UploadOut[]> {
  return request<UploadOut[]>(apiUrl('/api/roster'), init)
}

export function previewRoster(file: File): Promise<PreviewOut> {
  const form = new FormData()
  form.append('file', file)
  return request<PreviewOut>(apiUrl('/api/roster/preview'), {
    method: 'POST',
    body: form,
  })
}

export function commitRoster(uploadId: string): Promise<UploadOut> {
  return request<UploadOut>(apiUrl(`/api/roster/${uploadId}/commit`), {
    method: 'POST',
  })
}

export function discardRoster(uploadId: string): Promise<null> {
  return request<null>(apiUrl(`/api/roster/${uploadId}`), {
    method: 'DELETE',
  })
}

export function clearRoster(): Promise<ClearRosterOut> {
  return request<ClearRosterOut>(apiUrl('/api/roster/members'), {
    method: 'DELETE',
  })
}

export function listMembers(
  filters: MemberFilters = {},
  init?: RequestInit,
): Promise<MembersPage> {
  const params = new URLSearchParams()
  if (filters.name?.trim()) params.set('name', filters.name.trim())
  if (filters.dodid?.trim()) params.set('dodid', filters.dodid.trim())
  if (filters.afsc?.trim()) params.set('afsc', filters.afsc.trim())
  if (filters.personnel_type) params.set('personnel_type', filters.personnel_type)
  params.set('limit', String(filters.limit ?? 25))
  params.set('offset', String(filters.offset ?? 0))
  const query = params.toString()
  return request<MembersPage>(apiUrl(`/api/members?${query}`), init)
}

export function checkTeam(
  body: TeamCheckRequest,
  init?: RequestInit,
): Promise<TeamCheckResponse> {
  return request<TeamCheckResponse>(apiUrl('/api/members/team-check'), {
    ...init,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    body: JSON.stringify(body),
  })
}

export function getAfscSearchLabels(
  pattern: string,
  init?: RequestInit,
): Promise<SearchLabelsOut> {
  const params = new URLSearchParams({ pattern })
  return request<SearchLabelsOut>(apiUrl(`/api/afsc/search-labels?${params}`), init)
}

export function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === 'AbortError') ||
    (err instanceof Error && err.name === 'AbortError')
  )
}

export function getAfscCatalog(init?: RequestInit): Promise<CatalogOut> {
  return request<CatalogOut>(apiUrl('/api/afsc/catalog'), init)
}

export function sendChat(
  messages: ChatMessage[],
  init?: RequestInit,
): Promise<ChatResponse> {
  return request<ChatResponse>(apiUrl('/api/chat'), {
    ...init,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    body: JSON.stringify({ messages }),
  })
}
