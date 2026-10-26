import { request } from './client'
import type { Project, ProjectDetails, ProjectWorkbench, CreateProjectRequest } from '../types/api'

export async function listProjects(): Promise<{ projects: Project[] }> {
  return request('/projects')
}

export async function getProject(name: string): Promise<ProjectDetails> {
  return request(`/projects/${encodeURIComponent(name)}`)
}

export async function getProjectWorkbench(name: string): Promise<ProjectWorkbench> {
  return request(`/projects/${encodeURIComponent(name)}/workbench`)
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
