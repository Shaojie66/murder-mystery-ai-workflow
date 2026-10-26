import { create } from 'zustand'
import type { Project, ProjectDetails, ProjectWorkbench } from '../types/api'

interface ProjectStore {
  projects: Project[]
  currentProject: ProjectDetails | null
  currentWorkbench: ProjectWorkbench | null
  currentProjectName: string | null
  loading: boolean
  error: string | null

  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: ProjectDetails | null) => void
  setCurrentWorkbench: (workbench: ProjectWorkbench | null) => void
  clearCurrentProjectContext: () => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  currentProject: null,
  currentWorkbench: null,
  currentProjectName: null,
  loading: false,
  error: null,

  setProjects: (projects) => set({ projects }),
  setCurrentProject: (currentProject) => set({
    currentProject,
    currentProjectName: currentProject?.name ?? null,
  }),
  setCurrentWorkbench: (currentWorkbench) => set({
    currentWorkbench,
    currentProject: currentWorkbench?.project ?? null,
    currentProjectName: currentWorkbench?.project.name ?? null,
  }),
  clearCurrentProjectContext: () => set({
    currentProject: null,
    currentWorkbench: null,
    currentProjectName: null,
    loading: false,
    error: null,
  }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}))
