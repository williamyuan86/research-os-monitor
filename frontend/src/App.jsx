import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import Assets from './pages/Assets'
import Alerts from './pages/Alerts'
import Reports from './pages/Reports'
import KnowledgeGraph from './pages/KnowledgeGraph'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="assets" element={<Assets />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="reports" element={<Reports />} />
          <Route path="knowledge-graph" element={<KnowledgeGraph />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
