import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle, Info, AlertCircle, Filter, Plus } from 'lucide-react'
import { listAlerts, createAlert, resolveAlert } from '../utils/api'

const SEVERITY_ICONS = {
  critical: AlertCircle,
  error: AlertTriangle,
  warning: AlertTriangle,
  info: Info
}

const SEVERITY_COLORS = {
  critical: 'bg-red-50 border-red-500 text-red-700',
  error: 'bg-orange-50 border-orange-500 text-orange-700',
  warning: 'bg-yellow-50 border-yellow-500 text-yellow-700',
  info: 'bg-blue-50 border-blue-500 text-blue-700'
}

const ALERT_TYPES = ['stage_blocked', 'cache_miss', 'asset_health', 'system']

function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [filter, setFilter] = useState({ resolved: null, severity: '' })
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({ alert_id: '', type: 'system', severity: 'info', message: '', project_id: null })
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadAlerts() }, [filter])

  async function loadAlerts() {
    setLoading(true)
    try {
      const params = {}
      if (filter.resolved !== null) params.resolved = filter.resolved
      if (filter.severity) params.severity = filter.severity
      setAlerts(await listAlerts(params))
    } catch (err) {
      console.error('Failed to load alerts:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    try {
      await createAlert({ ...formData, alert_id: `alert_${Date.now()}` })
      setShowModal(false)
      setFormData({ alert_id: '', type: 'system', severity: 'info', message: '', project_id: null })
      loadAlerts()
    } catch (err) {
      console.error('Failed to create alert:', err)
    }
  }

  async function handleResolve(id) {
    try {
      await resolveAlert(id, { is_resolved: true })
      loadAlerts()
    } catch (err) {
      console.error('Failed to resolve alert:', err)
    }
  }

  const activeAlerts = alerts.filter(a => !a.is_resolved)
  const resolvedAlerts = alerts.filter(a => a.is_resolved)

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          <p className="text-gray-500">Monitor system alerts and warnings</p>
        </div>
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
          <Plus className="w-4 h-4" /> New Alert
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg"><AlertCircle className="w-5 h-5 text-red-600" /></div>
            <div><p className="text-2xl font-bold">{activeAlerts.filter(a => a.severity === 'critical').length}</p><p className="text-sm text-gray-500">Critical</p></div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg"><AlertTriangle className="w-5 h-5 text-orange-600" /></div>
            <div><p className="text-2xl font-bold">{activeAlerts.filter(a => a.severity === 'error').length}</p><p className="text-sm text-gray-500">Error</p></div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 rounded-lg"><AlertTriangle className="w-5 h-5 text-yellow-600" /></div>
            <div><p className="text-2xl font-bold">{activeAlerts.filter(a => a.severity === 'warning').length}</p><p className="text-sm text-gray-500">Warning</p></div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg"><CheckCircle className="w-5 h-5 text-green-600" /></div>
            <div><p className="text-2xl font-bold">{resolvedAlerts.length}</p><p className="text-sm text-gray-500">Resolved</p></div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <select value={filter.resolved === null ? '' : filter.resolved} onChange={(e) => setFilter({ ...filter, resolved: e.target.value === '' ? null : e.target.value === 'true' })} className="px-4 py-2 border border-gray-300 rounded-lg">
          <option value="">All Status</option>
          <option value="false">Active</option>
          <option value="true">Resolved</option>
        </select>
        <select value={filter.severity} onChange={(e) => setFilter({ ...filter, severity: e.target.value })} className="px-4 py-2 border border-gray-300 rounded-lg">
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="error">Error</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
      </div>

      {/* Alerts List */}
      {loading ? (
        <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div></div>
      ) : alerts.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <p className="text-gray-500">No alerts found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const Icon = SEVERITY_ICONS[alert.severity] || Info
            return (
              <div key={alert.id} className={`bg-white rounded-xl shadow-sm border-l-4 p-4 ${SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.info} ${alert.is_resolved ? 'opacity-60' : ''}`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <Icon className="w-5 h-5 mt-0.5" />
                    <div>
                      <p className="font-medium">{alert.message}</p>
                      <div className="flex items-center gap-3 mt-2 text-sm">
                        <span className="px-2 py-0.5 bg-white/50 rounded text-xs">{alert.type}</span>
                        <span className="text-gray-500">{new Date(alert.created_at).toLocaleString()}</span>
                        {alert.project_id && <span className="text-gray-500">Project: {alert.project_id}</span>}
                      </div>
                    </div>
                  </div>
                  {!alert.is_resolved && (
                    <button onClick={() => handleResolve(alert.id)} className="flex items-center gap-1 px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700">
                      <CheckCircle className="w-4 h-4" /> Resolve
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Create Alert</h2>
            <form onSubmit={handleCreate}>
              <div className="space-y-4">
                <div><label className="block text-sm font-medium mb-1">Type</label><select value={formData.type} onChange={(e) => setFormData({...formData, type: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2">{ALERT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}</select></div>
                <div><label className="block text-sm font-medium mb-1">Severity</label><select value={formData.severity} onChange={(e) => setFormData({...formData, severity: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2"><option value="info">Info</option><option value="warning">Warning</option><option value="error">Error</option><option value="critical">Critical</option></select></div>
                <div><label className="block text-sm font-medium mb-1">Message</label><textarea value={formData.message} onChange={(e) => setFormData({...formData, message: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2" rows={3} required /></div>
                <div><label className="block text-sm font-medium mb-1">Project ID (optional)</label><input type="number" value={formData.project_id || ''} onChange={(e) => setFormData({...formData, project_id: e.target.value ? parseInt(e.target.value) : null})} className="w-full border border-gray-300 rounded-lg px-3 py-2" /></div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Alerts
