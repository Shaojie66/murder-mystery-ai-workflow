import { request } from './client'
import type { CostSummary, CharacterMatrix } from '../types/api'

// Files
export async function listFiles(projectName: string) {
  const name = encodeURIComponent(projectName)
  return request<{ files: Array<{ name: string; type: string; size: number; modified: string }> }>(
    `/projects/${name}/files`
  )
}

export async function getFile(projectName: string, filename: string) {
  const name = encodeURIComponent(projectName)
  const file = encodeURIComponent(filename)
  return request<{ name: string; content: string; type: string; size: number; modified: string }>(
    `/projects/${name}/files/${file}`
  )
}

export async function saveFile(projectName: string, filename: string, content: string) {
  const name = encodeURIComponent(projectName)
  const file = encodeURIComponent(filename)
  return request(`/projects/${name}/files/${file}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  })
}

// Matrix
export async function getMatrix(projectName: string): Promise<CharacterMatrix> {
  const name = encodeURIComponent(projectName)
  return request(`/projects/${name}/matrix`)
}

export async function updateMatrixCell(
  projectName: string,
  charId: string,
  eventId: string,
  state: string,
  detail: string = '',
  evidenceRefs: string[] = []
) {
  const name = encodeURIComponent(projectName)
  return request(`/projects/${name}/matrix/cells/${charId}/${eventId}`, {
    method: 'PUT',
    body: JSON.stringify({ state, detail, evidence_refs: evidenceRefs }),
  })
}

export async function initializeMatrix(
  projectName: string,
  charCount: number = 6,
  eventCount: number = 7,
  isPrototype: boolean = false
) {
  const name = encodeURIComponent(projectName)
  return request(`/projects/${name}/matrix/initialize`, {
    method: 'POST',
    body: JSON.stringify({ char_count: charCount, event_count: eventCount, is_prototype: isPrototype }),
  })
}

// Costs
export async function getCosts(projectName: string): Promise<CostSummary> {
  const name = encodeURIComponent(projectName)
  return request(`/projects/${name}/costs`)
}

// Phase running status
export async function getPhaseStatus(projectName: string, stage: number) {
  const name = encodeURIComponent(projectName)
  return request<{ running: boolean }>(`/projects/${name}/phases/${stage}/status`)
}
