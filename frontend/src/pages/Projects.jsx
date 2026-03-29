import { useEffect, useState } from 'react'
import { Plus, Edit, Trash2, Play, Pause, CheckCircle } from 'lucide-react'
import { listProjects, createProject, updateProject, deleteProject, listStages, updateStage } from '../utils/api'

const PHASES = ['discovery', 'triage', 'analysis', 'synthesis', 'writing']
const PHASE_LABELS = {
  discovery: 'Discovery',
  triage: 'Triage',
  analysis: 'Analysis',
  synthesis: 'Synthesis',
  writing: 'Writing'
}

function Projects() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(null)
  const [stages, setStages] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({ name: '', current_phase: 'discovery', status: 'idle' })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadProjects()
  }, [])

  useEffect(() => {
    if (selectedProject) {
      listStages(selectedProject.id).then(setStages).catch(console.error)
    }
  }, [selectedProject])

  async function loadProjects() {
    try {
      const data = await listProjects({ limit: 100 })
      setProjects(data)
      if (data.length > 0 && !selectedProject) {
        setSelectedProject(data[0])
      }
    } catch (err) {
      console.error('Failed to load projects:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    try {
      await createProject(formData)
      setShowModal(false)
      setFormData({ name: '', current_phase: 'discovery', status: 'idle' })
      loadProjects()
    } catch (err) {
      console.error('Failed to create project:', err)
    }
  }

  async function handleUpdateStatus(projectId, status) {
    try {
      await updateProject(projectId, { status })
      loadProjects()
    } catch (err) {
      console.error('Failed to update status:', err)
    }
  }

  async function handleDelete(projectId) {
    if (!confirm('Are you sure you want to delete this project?')) return
    try {
      await deleteProject(projectId)
      if (selectedProject?.id === projectId) {
        setSelectedProject(null)
        setStages([])
      }
      loadProjects()
    } catch (err) {
      console.error('Failed to delete project:', err)
    }
  }

  async function handleStageUpdate(stageId, data) {
    try {
      await updateStage(stageId, data)
      if (selectedProject) {
        const updated = await listStages(selectedProject.id)
        setStages(updated)
      }
    } catch (err) {
      console.error('Failed to update stage:', err)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div></div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-500">Manage research projects and stages</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Project List */}
        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <h3 className="font-semibold mb-4">All Projects</h3>
          <div className="space-y-2">
            {projects.map((project) => (
              <div
                key={project.id}
                onClick={() => setSelectedProject(project)}
                className={`p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedProject?.id === project.id
                    ? 'bg-primary-50 border border-primary-200'
                    : 'hover:bg-gray-50 border border-transparent'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium">{project.name}</p>
                    <p className="text-sm text-gray-500">
                      {PHASE_LABELS[project.current_phase]} • {project.status}
                    </p>
                  </div>
                  <span className="text-xs text-gray-400">
                    {Math.round(project.completion_ratio * 100)}%
                  </span>
                </div>
              </div>
            ))}
            {projects.length === 0 && (
              <p className="text-gray-500 text-center py-8">No projects yet</p>
            )}
          </div>
        </div>

        {/* Project Details */}
        <div className="lg:col-span-2 space-y-6">
          {selectedProject ? (
            <>
              {/* Header */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className="text-xl font-bold">{selectedProject.name}</h2>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="px-3 py-1 text-sm rounded-full bg-blue-100 text-blue-700">
                        {PHASE_LABELS[selectedProject.current_phase]}
                      </span>
                      <span className={`px-3 py-1 text-sm rounded-full ${
                        selectedProject.status === 'running' ? 'bg-green-100 text-green-700' :
                        selectedProject.status === 'completed' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {selectedProject.status}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {selectedProject.status === 'running' ? (
                      <button
                        onClick={() => handleUpdateStatus(selectedProject.id, 'paused')}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        onClick={() => handleUpdateStatus(selectedProject.id, 'running')}
                        className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(selectedProject.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="mt-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">Overall Progress</span>
                    <span className="font-medium">{Math.round(selectedProject.completion_ratio * 100)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-500 h-2 rounded-full transition-all"
                      style={{ width: `${selectedProject.completion_ratio * 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Stage Runs */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 className="font-semibold mb-4">Stage Progress</h3>
                <div className="space-y-4">
                  {stages.map((stage) => (
                    <div key={stage.id} className="p-4 border border-gray-200 rounded-lg">
                      <div className="flex justify-between items-center mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{PHASE_LABELS[stage.stage_name]}</span>
                          {stage.claimed_status === 'completed' && (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <select
                            value={stage.claimed_status}
                            onChange={(e) => handleStageUpdate(stage.id, { claimed_status: e.target.value })}
                            className="text-sm border border-gray-300 rounded px-2 py-1"
                          >
                            <option value="pending">Pending</option>
                            <option value="running">Running</option>
                            <option value="completed">Completed</option>
                            <option value="failed">Failed</option>
                          </select>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full transition-all ${
                            stage.claimed_status === 'completed' ? 'bg-green-500' :
                            stage.claimed_status === 'failed' ? 'bg-red-500' :
                            'bg-blue-500'
                          }`}
                          style={{ width: `${stage.completion_ratio * 100}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between mt-2 text-xs text-gray-500">
                        <span>Progress: {Math.round(stage.completion_ratio * 100)}%</span>
                        <span>Verified: {stage.verified_status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
              <p className="text-gray-500">Select a project to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Create New Project</h2>
            <form onSubmit={handleCreate}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Project Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Initial Phase</label>
                  <select
                    value={formData.current_phase}
                    onChange={(e) => setFormData({ ...formData, current_phase: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  >
                    {PHASES.map((phase) => (
                      <option key={phase} value={phase}>{PHASE_LABELS[phase]}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Projects
