import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ProjectView from './pages/ProjectView'
import PhaseExecution from './pages/PhaseExecution'
import FileEditor from './pages/FileEditor'
import MatrixEditor from './pages/MatrixEditor'
import AuditView from './pages/AuditView'
import CostPage from './pages/CostPage'
import Layout from './components/layout/Layout'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects/:name" element={<ProjectView />} />
          <Route path="/projects/:name/phase/:stage" element={<PhaseExecution />} />
          <Route path="/projects/:name/files/:filename" element={<FileEditor />} />
          <Route path="/projects/:name/matrix" element={<MatrixEditor />} />
          <Route path="/projects/:name/audit" element={<AuditView />} />
          <Route path="/projects/:name/costs" element={<CostPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
