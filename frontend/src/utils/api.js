const API_BASE = '/api'

async function fetchAPI(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`)
  }
  
  return response.json()
}

// Dashboard
export const getDashboardStats = () => fetchAPI('/dashboard/stats')
export const getProjectPhases = (projectId) => fetchAPI(`/dashboard/phases/${projectId}`)

// Projects
export const listProjects = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return fetchAPI(`/projects${query ? `?${query}` : ''}`)
}
export const getProject = (id) => fetchAPI(`/projects/${id}`)
export const createProject = (data) => fetchAPI('/projects', { method: 'POST', body: JSON.stringify(data) })
export const updateProject = (id, data) => fetchAPI(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
export const deleteProject = (id) => fetchAPI(`/projects/${id}`, { method: 'DELETE' })

// Stage Runs
export const listStages = (projectId) => fetchAPI(`/projects/${projectId}/stages`)
export const updateStage = (stageId, data) => fetchAPI(`/stages/${stageId}`, { method: 'PATCH', body: JSON.stringify(data) })

// Paper Assets
export const listPapers = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return fetchAPI(`/assets/papers${query ? `?${query}` : ''}`)
}
export const createPaper = (data) => fetchAPI('/assets/papers', { method: 'POST', body: JSON.stringify(data) })
export const updatePaper = (id, data) => fetchAPI(`/assets/papers/${id}`, { method: 'PATCH', body: JSON.stringify(data) })

// Code Assets
export const listCodeAssets = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return fetchAPI(`/assets/code${query ? `?${query}` : ''}`)
}
export const createCodeAsset = (data) => fetchAPI('/assets/code', { method: 'POST', body: JSON.stringify(data) })

// Experiment Assets
export const listExperiments = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return fetchAPI(`/assets/experiments${query ? `?${query}` : ''}`)
}

// Graph Assets
export const listGraphs = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return fetchAPI(`/assets/graphs${query ? `?${query}` : ''}`)
}

// Alerts
export const listAlerts = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return fetchAPI(`/alerts${query ? `?${query}` : ''}`)
}
export const createAlert = (data) => fetchAPI('/alerts', { method: 'POST', body: JSON.stringify(data) })
export const resolveAlert = (id, data) => fetchAPI(`/alerts/${id}`, { method: 'PATCH', body: JSON.stringify(data) })

// Reports
export const listReports = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return fetchAPI(`/reports${query ? `?${query}` : ''}`)
}
export const createReport = (data) => fetchAPI('/reports', { method: 'POST', body: JSON.stringify(data) })

// Knowledge Graph & Ingest
export const scanProjects = () => fetchAPI('/ingest/scan')
export const ingestProject = (slug) => fetchAPI(`/ingest/${slug}`, { method: 'POST' })
export const autoIngestAll = () => fetchAPI('/ingest/auto/all', { method: 'POST' })
export const getKnowledgeGraph = (slug) => fetchAPI(`/graphs/knowledge/${slug}`)
