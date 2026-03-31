import { request } from './client'
import type { Project, ProjectDetails, CreateProjectRequest } from '../types/api'

export async function listProjects(): Promise<{ projects: Project[] }> {
  return request('/projects')
}

export async function getProject(name: string): Promise<ProjectDetails> {
  return request(`/projects/${encodeURIComponent(name)}`)
}

export async function createProject(req: CreateProjectRequest): Promise<{ name: string; status: string }> {
  return request('/projects', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function deleteProject(name: string): Promise<{ deleted: string }> {
  return request(`/projects/${encodeURIComponent(name)}`, { method: 'DELETE' })
}
