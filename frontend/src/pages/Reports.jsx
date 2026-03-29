import { useEffect, useState } from 'react'
import { FileText, Download, Calendar, Plus } from 'lucide-react'
import { listReports, createReport, getDashboardStats, listProjects, listAlerts } from '../utils/api'

const REPORT_TYPES = [
  { id: 'daily', label: 'Daily Report' },
  { id: 'weekly', label: 'Weekly Report' },
  { id: 'monthly', label: 'Monthly Report' },
  { id: 'custom', label: 'Custom Report' }
]

async function generateReportContent(type) {
  const [stats, projects, alerts] = await Promise.all([
    getDashboardStats(),
    listProjects({ limit: 50 }),
    listAlerts({ resolved: false, limit: 100 })
  ])

  const content = {
    summary: {
      totalProjects: stats.total_projects,
      activeProjects: stats.active_projects,
      completedProjects: stats.completed_projects,
      totalPapers: stats.total_papers,
      papersAnalyzed: stats.papers_analyzed,
      totalCodeAssets: stats.total_code_assets,
      totalExperiments: stats.total_experiments,
      experimentsCompleted: stats.experiments_completed,
      activeAlerts: stats.active_alerts,
      criticalAlerts: stats.critical_alerts
    },
    projects: projects.map(p => ({
      id: p.id,
      name: p.name,
      phase: p.current_phase,
      status: p.status,
      progress: p.completion_ratio
    })),
    alerts: alerts.map(a => ({
      id: a.id,
      type: a.type,
      severity: a.severity,
      message: a.message,
      createdAt: a.created_at
    })),
    generatedAt: new Date().toISOString()
  }

  return content
}

function Reports() {
  const [reports, setReports] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [selectedReport, setSelectedReport] = useState(null)

  useEffect(() => { loadReports() }, [])

  async function loadReports() {
    try {
      setReports(await listReports())
    } catch (err) {
      console.error('Failed to load reports:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate(e) {
    e.preventDefault()
    setGenerating(true)
    try {
      const content = await generateReportContent('custom')
      const reportData = {
        report_id: `report_${Date.now()}`,
        report_type: 'custom',
        content: JSON.stringify(content)
      }
      await createReport(reportData)
      setShowModal(false)
      loadReports()
    } catch (err) {
      console.error('Failed to generate report:', err)
    } finally {
      setGenerating(false)
    }
  }

  function formatReportType(type) {
    return REPORT_TYPES.find(t => t.id === type)?.label || type
  }

  function renderReportContent(content) {
    try {
      const data = typeof content === 'string' ? JSON.parse(content) : content
      return (
        <div className="space-y-6">
          {/* Summary Stats */}
          <div>
            <h4 className="font-semibold mb-3">Summary</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-2xl font-bold">{data.summary?.totalProjects || 0}</p>
                <p className="text-sm text-gray-500">Total Projects</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-2xl font-bold">{data.summary?.activeProjects || 0}</p>
                <p className="text-sm text-gray-500">Active</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-2xl font-bold">{data.summary?.totalPapers || 0}</p>
                <p className="text-sm text-gray-500">Papers</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-2xl font-bold">{data.summary?.activeAlerts || 0}</p>
                <p className="text-sm text-gray-500">Active Alerts</p>
              </div>
            </div>
          </div>

          {/* Projects */}
          {data.projects && data.projects.length > 0 && (
            <div>
              <h4 className="font-semibold mb-3">Projects ({data.projects.length})</h4>
              <div className="space-y-2">
                {data.projects.slice(0, 5).map((p, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <span className="font-medium">{p.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500">{p.phase}</span>
                      <span className={`px-2 py-0.5 text-xs rounded ${p.status === 'running' ? 'bg-green-100 text-green-700' : p.status === 'completed' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}>{p.status}</span>
                    </div>
                  </div>
                ))}
                {data.projects.length > 5 && <p className="text-sm text-gray-500">+{data.projects.length - 5} more</p>}
              </div>
            </div>
          )}

          {/* Alerts */}
          {data.alerts && data.alerts.length > 0 && (
            <div>
              <h4 className="font-semibold mb-3">Active Alerts ({data.alerts.length})</h4>
              <div className="space-y-2">
                {data.alerts.slice(0, 5).map((a, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <span className="text-sm">{a.message}</span>
                    <span className={`px-2 py-0.5 text-xs rounded ${a.severity === 'critical' ? 'bg-red-100 text-red-700' : a.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-700'}`}>{a.severity}</span>
                  </div>
                ))}
                {data.alerts.length > 5 && <p className="text-sm text-gray-500">+{data.alerts.length - 5} more</p>}
              </div>
            </div>
          )}

          <p className="text-sm text-gray-400">Generated: {new Date(data.generatedAt || data.generated_at).toLocaleString()}</p>
        </div>
      )
    } catch {
      return <pre className="text-sm overflow-auto p-4 bg-gray-50 rounded">{typeof content === 'string' ? content : JSON.stringify(content, null, 2)}</pre>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-500">Generate and view research reports</p>
        </div>
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
          <Plus className="w-4 h-4" /> Generate Report
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Reports List */}
        <div className="lg:col-span-1 space-y-4">
          <h3 className="font-semibold">Generated Reports</h3>
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div></div>
          ) : reports.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
              <FileText className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <p className="text-gray-500">No reports yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              {reports.map((report) => (
                <div
                  key={report.id}
                  onClick={() => setSelectedReport(report)}
                  className={`p-4 bg-white rounded-xl shadow-sm border cursor-pointer transition-colors ${
                    selectedReport?.id === report.id ? 'border-primary-500 ring-2 ring-primary-100' : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium">{formatReportType(report.report_type)}</p>
                      <p className="text-sm text-gray-500">{new Date(report.generated_at).toLocaleString()}</p>
                    </div>
                    <FileText className="w-5 h-5 text-gray-400" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Report Detail */}
        <div className="lg:col-span-2">
          {selectedReport ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold">{formatReportType(selectedReport.report_type)}</h2>
                  <p className="text-sm text-gray-500">Generated: {new Date(selectedReport.generated_at).toLocaleString()}</p>
                </div>
                <button className="flex items-center gap-2 px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
                  <Download className="w-4 h-4" /> Download
                </button>
              </div>
              {renderReportContent(selectedReport.content)}
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Select a report to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Generate Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Generate Report</h2>
            <form onSubmit={handleGenerate}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Report Type</label>
                  <div className="grid grid-cols-2 gap-2">
                    {REPORT_TYPES.map((type) => (
                      <label key={type.id} className="flex items-center gap-2 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                        <input type="radio" name="report_type" value={type.id} defaultChecked className="text-primary-600" />
                        <span className="text-sm">{type.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">The report will include:</p>
                  <ul className="mt-2 text-sm text-gray-500 list-disc list-inside">
                    <li>Project statistics and status</li>
                    <li>Paper and asset counts</li>
                    <li>Active alerts summary</li>
                    <li>Stage completion ratios</li>
                  </ul>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
                <button type="submit" disabled={generating} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
                  {generating ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Reports
