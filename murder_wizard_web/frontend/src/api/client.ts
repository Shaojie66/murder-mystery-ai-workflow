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

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

let tokenPromise: Promise<void> | null = null

export async function ensureToken(force = false): Promise<void> {
  if (force) clearToken()
  if (!force && getToken()) return
  if (tokenPromise) return tokenPromise

  tokenPromise = fetch(`${BASE}/user/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: getUserId() }),
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      return res.json() as Promise<{ token?: string }>
    })
    .then((data) => {
      if (!data.token) throw new Error('Token response missing token')
      setToken(data.token)
    })
    .finally(() => {
      tokenPromise = null
    })

  return tokenPromise
}

async function fetchWithRetry(path: string, options?: RequestInit, retryOn401 = true): Promise<Response> {
  await ensureToken()

  const token = getToken()
  const headers = new Headers(options?.headers ?? {})
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${BASE}${path}`, { ...options, headers })
  if (response.status !== 401 || !retryOn401) return response

  await ensureToken(true)
  const refreshed = getToken()
  const retryHeaders = new Headers(options?.headers ?? {})
  if (refreshed) retryHeaders.set('Authorization', `Bearer ${refreshed}`)
  return fetch(`${BASE}${path}`, { ...options, headers: retryHeaders })
}

export async function fetchWithAuth(path: string, options?: RequestInit): Promise<Response> {
  return fetchWithRetry(path, options, true)
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers ?? {})
  if (options?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetchWithRetry(path, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}
