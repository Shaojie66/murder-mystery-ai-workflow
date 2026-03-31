// Base API client for murder-wizard web backend

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

// SSE client
export function createSSEClient(url: string) {
  const events = new EventSource(url)

  return {
    events,
    close() {
      events.close()
    },
  }
}

// Re-export for convenience
export { request }
