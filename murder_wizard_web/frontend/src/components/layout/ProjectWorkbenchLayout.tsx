import { Outlet, useOutletContext, useParams } from 'react-router-dom'
import { useProjectWorkbench } from '../../hooks/useProjectWorkbench'
import type { ProjectDetails, ProjectWorkbench } from '../../types/api'

export interface ProjectWorkbenchContext {
  projectName: string
  project: ProjectDetails
  workbench: ProjectWorkbench
  refreshWorkbench: () => Promise<void>
}

export function useProjectWorkbenchContext() {
  return useOutletContext<ProjectWorkbenchContext>()
}

export default function ProjectWorkbenchLayout() {
  const { name } = useParams<{ name: string }>()
  const projectName = decodeURIComponent(name || '')
  const { workbench, project, loading, error, refresh } = useProjectWorkbench(projectName)

  if (loading && !workbench) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <span style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic' }}>
          加载项目工作台...
        </span>
      </div>
    )
  }

  if (error && (!workbench || !project)) {
    return (
      <div style={{ padding: '3rem', maxWidth: '720px', margin: '0 auto' }}>
        <div
          style={{
            padding: '1.5rem',
            border: '1px solid var(--output-error-border)',
            background: 'var(--output-error-bg)',
            color: 'var(--output-error)',
            fontFamily: "'Crimson Pro', serif",
            marginBottom: '1rem',
          }}
        >
          {error}
        </div>
        <button onClick={() => void refresh()} className="btn-primary" style={{ fontSize: '13px' }}>
          重新加载
        </button>
      </div>
    )
  }

  if (!workbench || !project) return null

  return (
    <Outlet
      context={{
        projectName,
        project,
        workbench,
        refreshWorkbench: refresh,
      }}
    />
  )
}
