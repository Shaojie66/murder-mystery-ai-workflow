import { fetchWithAuth, request } from './client'
import type { SSEEvent } from '../types/api'

export type RunMode = 'phase' | 'expand' | 'audit'

export interface RunPhaseStreamInput {
  projectName: string
  mode: RunMode
  stage?: number
  forceAudit?: boolean
  acceptOverwrite?: boolean
  analyze?: boolean
  onEvent: (event: SSEEvent) => void
}

function parseSSEBlock(block: string): SSEEvent | null {
  if (!block.trim() || block.startsWith(':')) return null

  let eventType = 'message'
  const dataLines: string[] = []

  for (const rawLine of block.split('\n')) {
    const line = rawLine.trimEnd()
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) {
      eventType = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trim())
    }
  }

  if (!dataLines.length) return null

  const rawData = dataLines.join('\n')
  try {
    return { type: eventType as SSEEvent['type'], data: JSON.parse(rawData) as Record<string, unknown> }
  } catch {
    return { type: eventType as SSEEvent['type'], data: { raw: rawData } }
  }
}

async function consumeEventStream(response: Response, onEvent: (event: SSEEvent) => void): Promise<void> {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done }).replace(/\r\n/g, '\n')

    let separatorIndex = buffer.indexOf('\n\n')
    while (separatorIndex !== -1) {
      const block = buffer.slice(0, separatorIndex)
      buffer = buffer.slice(separatorIndex + 2)
      const parsed = parseSSEBlock(block)
      if (parsed) onEvent(parsed)
      separatorIndex = buffer.indexOf('\n\n')
    }

    if (done) break
  }

  if (buffer.trim()) {
    const parsed = parseSSEBlock(buffer)
    if (parsed) onEvent(parsed)
  }
}

export async function runPhaseStream(input: RunPhaseStreamInput): Promise<void> {
  const { projectName, mode, stage, forceAudit = false, acceptOverwrite = false, analyze = false, onEvent } = input
  const name = encodeURIComponent(projectName)

  let path: string
  let body: string | undefined

  if (mode === 'expand') {
    path = `/projects/${name}/expand${acceptOverwrite ? '?accept_overwrite=true' : ''}`
  } else if (mode === 'audit') {
    path = `/projects/${name}/audit${forceAudit ? '?force=true' : ''}`
  } else {
    path = `/projects/${name}/phases/${stage}/run`
    body = JSON.stringify({ analyze })
  }

  const response = await fetchWithAuth(path, {
    method: 'POST',
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(err.detail || `HTTP ${response.status}`)
  }

  await consumeEventStream(response, onEvent)
}

export async function getPhaseStatus(projectName: string, stage: number) {
  const name = encodeURIComponent(projectName)
  return request<{ running: boolean }>(`/projects/${name}/phases/${stage}/status`)
}
