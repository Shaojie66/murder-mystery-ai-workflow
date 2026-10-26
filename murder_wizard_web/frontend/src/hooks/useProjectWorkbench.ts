import { useCallback, useEffect } from 'react'
import { getProjectWorkbench } from '../api/projects'
import { useProjectStore } from '../stores/projectStore'

export function useProjectWorkbench(projectName: string) {
  const {
    currentWorkbench,
    currentProject,
    currentProjectName,
    loading,
    error,
    setCurrentWorkbench,
    setLoading,
    setError,
  } = useProjectStore()

  const refresh = useCallback(async () => {
    if (!projectName) return
    try {
      setLoading(true)
      setError(null)
      const workbench = await getProjectWorkbench(projectName)
      setCurrentWorkbench(workbench)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [projectName, setCurrentWorkbench, setError, setLoading])

  useEffect(() => {
    if (!projectName) return
    if (currentProjectName === projectName && currentWorkbench) return
    void refresh()
  }, [currentProjectName, currentWorkbench, projectName, refresh])

  const scopedWorkbench = currentProjectName === projectName ? currentWorkbench : null
  const scopedProject = currentProjectName === projectName ? currentProject : null

  return {
    workbench: scopedWorkbench,
    project: scopedProject,
    loading: loading || currentProjectName !== projectName,
    error: currentProjectName === projectName ? error : null,
    refresh,
  }
}
