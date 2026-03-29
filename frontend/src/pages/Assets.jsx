import { useState, useEffect } from 'react';
import { FileText, Code, FlaskConical, Network, Search } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

export default function Assets() {
  const [activeTab, setActiveTab] = useState('papers');
  const [papers, setPapers] = useState([]);
  const [codeAssets, setCodeAssets] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [graphs, setGraphs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAssets();
  }, [activeTab]);

  const fetchAssets = async () => {
    setLoading(true);
    try {
      switch (activeTab) {
        case 'papers':
          const papersRes = await fetch(`${API_BASE}/assets/papers`);
          setPapers(await papersRes.json());
          break;
        case 'code':
          const codeRes = await fetch(`${API_BASE}/assets/code`);
          setCodeAssets(await codeRes.json());
          break;
        case 'experiments':
          const expRes = await fetch(`${API_BASE}/assets/experiments`);
          setExperiments(await expRes.json());
          break;
        case 'graphs':
          const graphRes = await fetch(`${API_BASE}/assets/graphs`);
          setGraphs(await graphRes.json());
          break;
      }
    } catch (err) {
      console.error('Failed to fetch assets:', err);
    }
    setLoading(false);
  };

  const getVerdictColor = (verdict) => {
    switch (verdict) {
      case 'DEEP_READ': return 'bg-green-100 text-green-800';
      case 'SKIM_ONLY': return 'bg-yellow-100 text-yellow-800';
      case 'REJECT': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'running': return 'text-blue-600';
      case 'failed': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const tabs = [
    { id: 'papers', label: '论文', icon: FileText },
    { id: 'code', label: '代码', icon: Code },
    { id: 'experiments', label: '实验', icon: FlaskConical },
    { id: 'graphs', label: '图谱', icon: Network },
  ];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">资产管理</h1>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 -mb-px ${
              activeTab === tab.id
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">加载中...</div>
      ) : (
        <>
          {/* Papers */}
          {activeTab === 'papers' && (
            <div className="space-y-3">
              {papers.length === 0 ? (
                <div className="text-center py-12 text-gray-500">暂无论文资产</div>
              ) : (
                papers.map(paper => (
                  <div key={paper.id} className="p-4 bg-white border rounded-lg">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium">{paper.title}</div>
                        <div className="text-sm text-gray-500 mt-1">
                          {paper.authors}
                        </div>
                        <div className="text-sm text-gray-400 mt-1">
                          Paper ID: {paper.paper_id}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {paper.verdict && (
                          <span className={`px-2 py-1 text-xs rounded ${getVerdictColor(paper.verdict)}`}>
                            {paper.verdict}
                          </span>
                        )}
                        <span className={`px-2 py-1 text-xs ${getStatusColor(paper.analysis_status)}`}>
                          {paper.analysis_status}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Code */}
          {activeTab === 'code' && (
            <div className="space-y-3">
              {codeAssets.length === 0 ? (
                <div className="text-center py-12 text-gray-500">暂无代码资产</div>
              ) : (
                codeAssets.map(code => (
                  <div key={code.id} className="p-4 bg-white border rounded-lg">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium">{code.repo_url}</div>
                        <div className="text-sm text-gray-500 mt-1">
                          License: {code.license || 'N/A'} | Stars: {code.stars || 0}
                        </div>
                        <div className="text-sm text-gray-400 mt-1">
                          Repo ID: {code.repo_id}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {code.official !== undefined && (
                          <span className={`px-2 py-1 text-xs rounded ${
                            code.official ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {code.official ? 'Official' : 'Discovered'}
                          </span>
                        )}
                        <span className={`px-2 py-1 text-xs ${getStatusColor(code.reproducibility_status)}`}>
                          {code.reproducibility_status}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Experiments */}
          {activeTab === 'experiments' && (
            <div className="space-y-3">
              {experiments.length === 0 ? (
                <div className="text-center py-12 text-gray-500">暂无实验资产</div>
              ) : (
                experiments.map(exp => (
                  <div key={exp.id} className="p-4 bg-white border rounded-lg">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium">实验 #{exp.id}</div>
                        <div className="text-sm text-gray-500 mt-1">
                          Project ID: {exp.project_id}
                        </div>
                        {exp.metrics && (
                          <div className="text-sm text-gray-400 mt-1">
                            Metrics: {JSON.stringify(exp.metrics)}
                          </div>
                        )}
                      </div>
                      <span className={`px-2 py-1 text-xs ${getStatusColor(exp.status)}`}>
                        {exp.status}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Graphs */}
          {activeTab === 'graphs' && (
            <div className="space-y-3">
              {graphs.length === 0 ? (
                <div className="text-center py-12 text-gray-500">暂无图谱资产</div>
              ) : (
                graphs.map(graph => (
                  <div key={graph.id} className="p-4 bg-white border rounded-lg">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium">图谱 #{graph.id}</div>
                        <div className="text-sm text-gray-500 mt-1">
                          Project ID: {graph.project_id}
                        </div>
                        <div className="text-sm text-gray-400 mt-1">
                          Nodes: {graph.node_count} | Edges: {graph.edge_count}
                        </div>
                      </div>
                      <div className="text-sm text-gray-500">
                        {graph.last_update && new Date(graph.last_update).toLocaleDateString('zh-CN')}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
