import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import ProjectView from './pages/ProjectView'
import PhaseExecution from './pages/PhaseExecution'
import FileEditor from './pages/FileEditor'
import MatrixEditor from './pages/MatrixEditor'
import AuditView from './pages/AuditView'
import CostPage from './pages/CostPage'
import Metrics from './pages/Metrics'
import Settings from './pages/Settings'
import Subscription from './pages/Subscription'
import Layout from './components/layout/Layout'
import ProjectWorkbenchLayout from './components/layout/ProjectWorkbenchLayout'
import { LandingA, LandingB, LandingPage } from './landing'
import { ensureToken } from './api/client'

export default function App() {
  useEffect(() => { ensureToken().catch(() => {}) }, [])
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/landing" element={<LandingPage />} />
        <Route path="/landing-a" element={<LandingA />} />
        <Route path="/landing-b" element={<LandingB />} />
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/subscription" element={<Subscription />} />
          <Route path="/projects/:name" element={<ProjectWorkbenchLayout />}>
            <Route index element={<ProjectView />} />
            <Route path="phase/:stage" element={<PhaseExecution />} />
            <Route path="files/*" element={<FileEditor />} />
            <Route path="matrix" element={<MatrixEditor />} />
            <Route path="audit" element={<AuditView />} />
            <Route path="costs" element={<CostPage />} />
          </Route>
          <Route path="/metrics" element={<Metrics />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
