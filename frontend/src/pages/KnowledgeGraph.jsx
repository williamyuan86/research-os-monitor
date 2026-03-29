import { useEffect, useRef, useState, useCallback } from 'react'
import cytoscape from 'cytoscape'
import { scanProjects, getKnowledgeGraph, ingestProject } from '../utils/api'

const TYPE_COLORS = {
  paper:   '#58a6ff',
  method:  '#a371f7',
  problem: '#f778ba',
  dataset: '#3fb950',
  metric:  '#d29922',
}

const TYPE_SIZES = {
  paper:   50,
  method:  35,
  problem: 30,
  dataset: 30,
  metric:  22,
}

const TYPE_LABELS_ZH = {
  paper:   '论文',
  method:  '方法',
  problem: '问题',
  dataset: '数据集',
  metric:  '指标',
}

const CYTO_STYLE = [
  {
    selector: 'node',
    style: {
      'background-color': (ele) => TYPE_COLORS[ele.data('type')] || '#666',
      'label': (ele) => {
        const t = ele.data('type')
        return `[${TYPE_LABELS_ZH[t] || t}] ${ele.data('label')}`
      },
      'color': '#8b949e',
      'font-size': '9px',
      'text-valign': 'bottom',
      'text-margin-y': 6,
      'width': (ele) => TYPE_SIZES[ele.data('type')] || 20,
      'height': (ele) => TYPE_SIZES[ele.data('type')] || 20,
      'border-width': 2,
      'border-color': (ele) => TYPE_COLORS[ele.data('type')] || '#666',
      'border-opacity': 0.8,
    },
  },
  {
    selector: 'edge',
    style: {
      'width': 1,
      'line-color': '#444c56',
      'target-arrow-color': '#444c56',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'opacity': 0.5,
    },
  },
  {
    selector: 'node:selected',
    style: { 'border-width': 4, 'border-color': '#fff' },
  },
  {
    selector: '.faded',
    style: { 'opacity': 0.12 },
  },
  {
    selector: '.highlighted',
    style: { 'opacity': 1, 'border-width': 4, 'border-color': '#fff' },
  },
]

function DetailPanel({ node, onClose }) {
  if (!node) return null
  const d = node.data()

  return (
    <div className="absolute top-0 right-0 h-full w-72 bg-gray-900 border-l border-gray-700 overflow-y-auto z-10 shadow-xl">
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-gray-100">节点详情</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-lg leading-none">×</button>
      </div>
      <div className="p-4 space-y-3 text-sm">
        {d.type === 'paper' ? (
          <>
            <Section label="论文标题" value={d.title || d.label} />
            <Section label="会议/期刊" value={d.venue || '—'} />
            <Section label="年份" value={d.year || '—'} />
            <Section label="核心主题" value={d.topic || '—'} />
            {d.abstract && <Section label="摘要" value={d.abstract} />}
            {(d.url || d.pdf || d.code) && (
              <div>
                <p className="text-xs text-gray-500 mb-1">相关链接</p>
                <div className="flex flex-wrap gap-2">
                  {d.url  && <a href={d.url}  target="_blank" rel="noreferrer" className="px-2 py-1 text-xs rounded bg-blue-800 text-blue-200 hover:bg-blue-700">📄 arXiv</a>}
                  {d.pdf  && <a href={d.pdf}  target="_blank" rel="noreferrer" className="px-2 py-1 text-xs rounded bg-purple-800 text-purple-200 hover:bg-purple-700">📑 PDF</a>}
                  {d.code && <a href={d.code} target="_blank" rel="noreferrer" className="px-2 py-1 text-xs rounded bg-green-800 text-green-200 hover:bg-green-700">💻 代码</a>}
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <Section label={`${TYPE_LABELS_ZH[d.type] || d.type}名称`} value={d.name || d.label} />
            <Section label="描述" value={d.desc || '—'} />
          </>
        )}
        {node.connectedNodes().length > 0 && (
          <div>
            <p className="text-xs text-gray-500 mb-1">关联节点 ({node.connectedNodes().length})</p>
            <div className="flex flex-wrap gap-1">
              {node.connectedNodes().map(n => (
                <span
                  key={n.id()}
                  className="px-1.5 py-0.5 text-xs rounded"
                  style={{ backgroundColor: TYPE_COLORS[n.data('type')] + '33', color: TYPE_COLORS[n.data('type')] }}
                >
                  {n.data('label')}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Section({ label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-gray-200 mt-0.5">{value}</p>
    </div>
  )
}

export default function KnowledgeGraph() {
  const cyRef = useRef(null)
  const containerRef = useRef(null)
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [layout, setLayout] = useState('cluster')
  const [filters, setFilters] = useState({ paper: true, method: true, problem: true, dataset: true, metric: true })
  const [stats, setStats] = useState({})
  const [selectedNode, setSelectedNode] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [ingesting, setIngesting] = useState(false)

  // Load project list on mount
  useEffect(() => {
    scanProjects()
      .then(data => {
        const list = data.projects || []
        setProjects(list)
        if (list.length > 0) setSelectedProject(list[0].slug)
      })
      .catch(() => setError('无法加载项目列表'))
  }, [])

  // Load graph when project changes
  useEffect(() => {
    if (!selectedProject) return
    if (!cyRef.current) initCy()
    loadGraph(selectedProject)
  }, [selectedProject])

  function initCy() {
    cyRef.current = cytoscape({
      container: containerRef.current,
      style: CYTO_STYLE,
      layout: { name: 'preset' },
    })
    cyRef.current.on('tap', 'node', evt => {
      setSelectedNode(evt.target)
      highlightConnected(evt.target)
    })
    cyRef.current.on('tap', evt => {
      if (evt.target === cyRef.current) {
        setSelectedNode(null)
        resetHighlight()
      }
    })
  }

  async function loadGraph(slug) {
    setLoading(true)
    setError(null)
    setSelectedNode(null)
    setStats({})
    try {
      const data = await getKnowledgeGraph(slug)
      // Compute stats directly from raw JSON — reliable, no Cytoscape API needed
      const newStats = {}
      for (const node of (data.nodes || [])) {
        const t = node?.data?.type
        if (t) newStats[t] = (newStats[t] || 0) + 1
      }
      setStats(newStats)
      const cy = cyRef.current
      cy.elements().remove()
      cy.add(data)
      runLayout(layout, true)
    } catch (e) {
      setError(`未找到 "${slug}" 的知识图谱数据`)
    } finally {
      setLoading(false)
    }
  }

  function updateStats(cy) {
    const nodes = cy.nodes()
    setStats({
      paper:   nodes.filter('[type="paper"]').length,
      method:  nodes.filter('[type="method"]').length,
      problem: nodes.filter('[type="problem"]').length,
      dataset: nodes.filter('[type="dataset"]').length,
      metric:  nodes.filter('[type="metric"]').length,
    })
  }

  function runLayout(type, fit = true) {
    const cy = cyRef.current
    if (!cy) return
    if (type === 'cluster') {
      const container = cy.container()
      const w = container.offsetWidth || 1000
      const h = container.offsetHeight || 700
      const centers = {
        paper:   { x: w * 0.25, y: h * 0.3 },
        method:  { x: w * 0.75, y: h * 0.3 },
        problem: { x: w * 0.25, y: h * 0.7 },
        dataset: { x: w * 0.75, y: h * 0.7 },
        metric:  { x: w * 0.5,  y: h * 0.5 },
      }
      const radius = Math.min(w, h) * 0.15
      ;['paper', 'method', 'problem', 'dataset', 'metric'].forEach(t => {
        const nodes = cy.nodes(`[type="${t}"]`).filter(':visible')
        if (!nodes.length) return
        nodes.forEach((n, i) => {
          const a = (2 * Math.PI * i) / nodes.length - Math.PI / 2
          const r = t === 'paper' ? radius * 1.2 : radius
          n.position({ x: centers[t].x + r * Math.cos(a), y: centers[t].y + r * Math.sin(a) })
        })
      })
      if (fit) setTimeout(() => cy.fit(60), 100)
    } else {
      cy.layout({
        name: 'cose',
        animate: true,
        animationDuration: 800,
        padding: 60,
        fit,
        nodeRepulsion: () => 6000,
        nodeOverlap: 20,
        idealEdgeLength: () => 100,
        edgeElasticity: () => 100,
        gravity: 50,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
        randomize: true,
      }).run()
    }
  }

  function highlightConnected(node) {
    resetHighlight()
    const connected = node.connectedNodes()
    const edges = node.connectedEdges()
    node.addClass('highlighted')
    connected.addClass('highlighted')
    edges.addClass('highlighted')
    cyRef.current.nodes().not(node).not(connected).addClass('faded')
    cyRef.current.edges().not(edges).addClass('faded')
  }

  function resetHighlight() {
    if (!cyRef.current) return
    cyRef.current.nodes().removeClass('faded highlighted')
    cyRef.current.edges().removeClass('faded highlighted')
  }

  function applyFilters(newFilters) {
    const cy = cyRef.current
    if (!cy) return
    cy.batch(() => {
      cy.nodes().forEach(n => {
        n.style('display', newFilters[n.data('type')] ? 'element' : 'none')
      })
    })
    runLayout(layout, true)
  }

  function handleFilterChange(type) {
    const next = { ...filters, [type]: !filters[type] }
    setFilters(next)
    applyFilters(next)
  }

  useEffect(() => {
    if (!cyRef.current) return
    const q = searchQuery.toLowerCase()
    if (!q) { resetHighlight(); return }
    cyRef.current.batch(() => {
      cyRef.current.nodes().forEach(n => {
        const match = (n.data('label') || '').toLowerCase().includes(q)
          || (n.data('title') || '').toLowerCase().includes(q)
          || (n.data('name') || '').toLowerCase().includes(q)
        n.removeClass('faded highlighted')
        n.addClass(match ? 'highlighted' : 'faded')
      })
    })
  }, [searchQuery])

  function handleLayoutChange(type) {
    setLayout(type)
    runLayout(type, true)
  }

  async function handleRefresh() {
    if (!selectedProject) return
    setIngesting(true)
    try {
      await ingestProject(selectedProject)
      await loadGraph(selectedProject)
    } catch {
      // ignore ingest errors, still try to load
      await loadGraph(selectedProject)
    } finally {
      setIngesting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">知识图谱</h1>
          <p className="text-gray-500 text-sm">Research OS 研究领域知识可视化</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={ingesting || loading}
          className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        >
          {ingesting ? '同步中...' : '↺ 同步数据'}
        </button>
      </div>

      <div className="flex gap-4 h-[calc(100vh-12rem)]">
        {/* Sidebar */}
        <div className="w-56 flex-shrink-0 space-y-4">
          {/* Project selector */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">当前项目</label>
            <select
              value={selectedProject || ''}
              onChange={e => setSelectedProject(e.target.value)}
              className="mt-1 w-full text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              {projects.map(p => (
                <option key={p.slug} value={p.slug}>{p.name}</option>
              ))}
            </select>
          </div>

          {/* Stats */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">统计概览</p>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(TYPE_LABELS_ZH).map(([type, label]) => (
                <div key={type} className="text-center">
                  <div className="text-lg font-bold" style={{ color: TYPE_COLORS[type] }}>{stats[type] || 0}</div>
                  <div className="text-xs text-gray-500">{label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">节点过滤</p>
            <div className="space-y-2">
              {Object.entries(TYPE_LABELS_ZH).map(([type, label]) => (
                <label key={type} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters[type]}
                    onChange={() => handleFilterChange(type)}
                    className="rounded"
                  />
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: TYPE_COLORS[type] }} />
                  <span className="text-sm text-gray-700">{label} ({stats[type] || 0})</span>
                </label>
              ))}
            </div>
          </div>

          {/* Search */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">搜索</p>
            <input
              type="text"
              placeholder="搜索节点..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>
        </div>

        {/* Graph area */}
        <div className="flex-1 bg-gray-900 rounded-xl overflow-hidden relative">
          {/* Toolbar */}
          <div className="absolute top-3 left-3 right-3 flex items-center justify-between z-10">
            <div className="flex gap-1">
              <button
                onClick={() => handleLayoutChange('cluster')}
                className={`px-3 py-1 text-xs rounded-lg transition-colors ${layout === 'cluster' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
              >⬡ 分类</button>
              <button
                onClick={() => handleLayoutChange('star')}
                className={`px-3 py-1 text-xs rounded-lg transition-colors ${layout === 'star' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
              >✦ 星状</button>
            </div>
            <div className="flex gap-1">
              <button
                onClick={() => runLayout(layout, true)}
                className="px-3 py-1 text-xs rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700"
              >重置视图</button>
              <button
                onClick={() => cyRef.current?.fit(50)}
                className="px-3 py-1 text-xs rounded-lg bg-blue-700 text-white hover:bg-blue-600"
              >适应画布</button>
            </div>
          </div>

          {/* Cytoscape container */}
          <div ref={containerRef} className="w-full h-full" />

          {/* Loading overlay */}
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-80">
              <div className="flex flex-col items-center gap-3">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-400" />
                <span className="text-gray-300 text-sm">加载知识图谱...</span>
              </div>
            </div>
          )}

          {/* Error overlay */}
          {error && !loading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-gray-400">
                <div className="text-4xl mb-3">🔍</div>
                <p className="text-sm">{error}</p>
                <p className="text-xs mt-1 text-gray-500">请先运行 knowledge-graph-builder 阶段，或点击"同步数据"</p>
              </div>
            </div>
          )}

          {/* Hint */}
          {!loading && !error && (
            <div className="absolute bottom-3 left-3 text-xs text-gray-600">
              🖱️ 拖拽平移 · 滚轮缩放 · 点击节点查看详情
            </div>
          )}

          {/* Detail panel */}
          {selectedNode && (
            <DetailPanel
              node={selectedNode}
              onClose={() => { setSelectedNode(null); resetHighlight() }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
