import type { Analytics, AuthResponse, Task, TaskInput, TaskPage, User } from '../types'

const TOKEN_KEY = 'ds360.token'

/** Token lives in sessionStorage: cleared when the tab closes (smaller exposure window
 * than localStorage). The strict CSP served by nginx is the primary XSS defence. */
export const tokenStore = {
  get(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token: string) {
    try {
      sessionStorage.setItem(TOKEN_KEY, token)
    } catch {
      /* storage unavailable: token stays in memory only */
    }
  },
  clear() {
    try {
      sessionStorage.removeItem(TOKEN_KEY)
    } catch {
      /* ignore */
    }
  },
}

export class ApiError extends Error {
  status: number
  fieldErrors: Record<string, string>

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const token = tokenStore.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let res: Response
  try {
    res = await fetch(path, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Network error — is the API reachable?')
  }

  if (res.status === 204) return undefined as T
  const body = await res.json().catch(() => ({}))

  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized()
    const fieldErrors: Record<string, string> = {}
    for (const e of body.errors ?? []) fieldErrors[e.field] = e.message
    const msg = typeof body.detail === 'string' ? body.detail : `Request failed (${res.status})`
    throw new ApiError(res.status, msg, fieldErrors)
  }
  return body as T
}

const json = (data: unknown) => JSON.stringify(data)

export interface TaskQuery {
  status?: string
  priority?: string
  q?: string
  sort?: string
  order?: 'asc' | 'desc'
  page?: number
  size?: number
  all_users?: boolean
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponse>('/api/v1/auth/login', { method: 'POST', body: json({ email, password }) }),
  register: (email: string, password: string, full_name: string) =>
    request<AuthResponse>('/api/v1/auth/register', {
      method: 'POST',
      body: json({ email, password, full_name }),
    }),
  me: () => request<User>('/api/v1/auth/me'),

  listTasks: (query: TaskQuery = {}) => {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== '' && v !== false) params.set(k, String(v))
    }
    return request<TaskPage>(`/api/v1/tasks?${params}`)
  },
  createTask: (input: TaskInput) =>
    request<Task>('/api/v1/tasks', { method: 'POST', body: json(input) }),
  updateTask: (id: number, input: Partial<TaskInput>) =>
    request<Task>(`/api/v1/tasks/${id}`, { method: 'PATCH', body: json(input) }),
  deleteTask: (id: number) => request<void>(`/api/v1/tasks/${id}`, { method: 'DELETE' }),

  analytics: (allUsers = false) =>
    request<Analytics>(`/api/v1/analytics/summary${allUsers ? '?all_users=true' : ''}`),

  listUsers: () => request<User[]>('/api/v1/users'),
  setRole: (id: number, role: string) =>
    request<User>(`/api/v1/users/${id}/role`, { method: 'PATCH', body: json({ role }) }),
  setActive: (id: number, active: boolean) =>
    request<User>(`/api/v1/users/${id}/active?active=${active}`, { method: 'PATCH' }),

  version: () => request<{ version: string; color: string; environment: string }>('/api/v1/version'),
}
