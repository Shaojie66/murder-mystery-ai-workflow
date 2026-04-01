const BASE = '/api'
const TOKEN_KEY = 'mw_token'
const USER_ID_KEY = 'mw_user_id'

export function getUserId(): string {
  let id = localStorage.getItem(USER_ID_KEY)
  if (!id) {
    id = `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
    localStorage.setItem(USER_ID_KEY, id)
  }
  return id
}

function getToken(): string | null { return localStorage.getItem(TOKEN_KEY) }
function setToken(token: string): void { localStorage.setItem(TOKEN_KEY, token) }

let tokenPromise: Promise<void> | null = null
export async function ensureToken(): Promise<void> {
  if (getToken()) return
  if (tokenPromise) return tokenPromise
  tokenPromise = fetch(`${BASE}/user/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: getUserId() }),
  }).then(r => r.json()).then(data => { if (data.token) setToken(data.token) })
    .catch(() => {}).finally(() => { tokenPromise = null })
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(options?.headers as Record<string, string> | undefined) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (res.status === 401 && token) {
    localStorage.removeItem(TOKEN_KEY)
    const retry = getToken()
    if (retry) {
      headers['Authorization'] = `Bearer ${retry}`
      const r = await fetch(`${BASE}${path}`, { ...options, headers })
      if (!r.ok) { const err = await r.json().catch(() => ({ detail: r.statusText })); throw new Error(err.detail || `HTTP ${r.status}`) }
      return r.json() as Promise<T>
    }
  }
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json() as Promise<T>
}

export function createSSEClient(url: string) {
  const events = new EventSource(url)
  return { events, close() { events.close() } }
}

export { request }
