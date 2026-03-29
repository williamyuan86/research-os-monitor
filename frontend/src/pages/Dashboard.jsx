import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts'
import { AlertTriangle, CheckCircle, Clock, Activity, Folder, FileText, Code, FlaskConical } from 'lucide-react'
import { getDashboardStats, getProjectPhases, listProjects, listAlerts } from '../utils/api'

const PHASE_COLORS = {
  discovery: '#3b82f6',
  triage: '#8b5cf6',
  analysis: '#10b981',
  synthesis: '#f59e0b',
  writing: '#ef4444'
}

const PHASE_LABELS = {
  discovery: 'Discovery',
  triage: 'Triage',
  analysis: 'Analysis',
  synthesis: 'Synthesis',
  writing: 'Writing'
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  )
}

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [projects, setProjects] = useState([])
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getDashboardStats(),
      listProjects({ limit: 10 }),
      listAlerts({ resolved: false, limit: 10 })
    ]).then(([statsData, projectsData, alertsData]) => {
      setStats(statsData)
      setProjects(projectsData)
      setAlerts(alertsData)
      setLoading(false)
    }).catch(err => {
      console.error('Failed to load dashboard data:', err)
      setLoading(false)
    })
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div></div>
  }

  // Prepare phase progress data
  const phaseData = Object.entries(PHASE_LABELS).map(([key, label]) => ({
    name: label,
    value: 20, // Mock data - in real app would come from project phases
    color: PHASE_COLORS[key]
  }))

  // Prepare project status data
  const projectStatusData = [
    { name: 'Active', value: stats?.active_projects || 0, color: '#10b981' },
    { name: 'Completed', value: stats?.completed_projects || 0, color: '#3b82f6' },
    { name: 'Idle', value: (stats?.total_projects || 0) - (stats?.active_projects || 0) - (stats?.completed_projects || 0), color: '#6b7280' }
  ]

  // Asset distribution
  const assetData = [
    { name: 'Papers', value: stats?.total_papers || 0 },
    { name: 'Code', value: stats?.total_code_assets || 0 },
    { name: 'Experiments', value: stats?.total_experiments || 0 }
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Research OS workflow monitoring overview</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={Folder} label="Total Projects" value={stats?.total_projects || 0} color="bg-blue-500" />
        <StatCard icon={Activity} label="Active Projects" value={stats?.active_projects || 0} color="bg-green-500" />
        <StatCard icon={FileText} label="Papers Analyzed" value={`${stats?.papers_analyzed || 0}/${stats?.total_papers || 0}`} color="bg-purple-500" />
        <StatCard icon={AlertTriangle} label="Active Alerts" value={stats?.active_alerts || 0} color={stats?.critical_alerts > 0 ? "bg-red-500" : "bg-yellow-500"} />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Project Status */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold mb-4">Project Status</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={projectStatusData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {projectStatusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-6 mt-4">
            {projectStatusData.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                <span className="text-sm text-gray-600">{item.name}: {item.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Asset Distribution */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold mb-4">Asset Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={assetData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Phase Progress & Alerts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Phase Progress */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold mb-4">Research Pipeline Progress</h3>
          <div className="space-y-4">
            {phaseData.map((phase) => (
              <div key={phase.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{phase.name}</span>
                  <span className="text-gray-500">{phase.value}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="h-2 rounded-full transition-all duration-500"
                    style={{ width: `${phase.value}%`, backgroundColor: phase.color }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Alerts</h3>
          {alerts.length === 0 ? (
            <div className="flex items-center gap-2 text-gray-500 py-8">
              <CheckCircle className="w-5 h-5" />
              <span>No active alerts</span>
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.slice(0, 5).map((alert) => (
                <div
                  key={alert.id}
                  className={`p-3 rounded-lg border-l-4 ${
                    alert.severity === 'critical' ? 'bg-red-50 border-red-500' :
                    alert.severity === 'error' ? 'bg-orange-50 border-orange-500' :
                    alert.severity === 'warning' ? 'bg-yellow-50 border-yellow-500' :
                    'bg-blue-50 border-blue-500'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className={`w-4 h-4 mt-0.5 ${
                      alert.severity === 'critical' ? 'text-red-500' :
                      alert.severity === 'error' ? 'text-orange-500' :
                      alert.severity === 'warning' ? 'text-yellow-500' :
                      'text-blue-500'
                    }`} />
                    <div>
                      <p className="text-sm font-medium">{alert.message}</p>
                      <p className="text-xs text-gray-500 mt-1">{new Date(alert.created_at).toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Projects */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Projects</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Name</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Phase</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Progress</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Created</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr key={project.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">{project.name}</td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">
                      {PHASE_LABELS[project.current_phase] || project.current_phase}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      project.status === 'running' ? 'bg-green-100 text-green-700' :
                      project.status === 'completed' ? 'bg-blue-100 text-blue-700' :
                      project.status === 'error' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {project.status}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-primary-500 h-1.5 rounded-full"
                          style={{ width: `${project.completion_ratio * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-500">{Math.round(project.completion_ratio * 100)}%</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-500">
                    {new Date(project.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
              {projects.length === 0 && (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-gray-500">
                    No projects yet. Create one to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
