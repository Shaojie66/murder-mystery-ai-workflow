import { create } from 'zustand'
import type { Project, ProjectDetails } from '../types/api'

interface ProjectStore {
  projects: Project[]
  currentProject: ProjectDetails | null
  loading: boolean
  error: string | null

  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: ProjectDetails | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  currentProject: null,
  loading: false,
  error: null,

  setProjects: (projects) => set({ projects }),
  setCurrentProject: (currentProject) => set({ currentProject }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}))
