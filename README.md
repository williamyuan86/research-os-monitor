# Research OS Monitor

科研流程监控和资产管理系统

## 技术栈

- **后端**: Python FastAPI + SQLite
- **前端**: React + Tailwind CSS + Recharts

## 项目结构

```
research-os-monitor/
├── backend/
│   ├── api/
│   │   ├── main.py       # FastAPI 应用入口
│   │   └── routes.py     # API 路由
│   ├── models/
│   │   ├── database.py   # SQLAlchemy 模型
│   │   └── schemas.py    # Pydantic schemas
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React 组件
│   │   ├── pages/        # 页面组件
│   │   ├── utils/        # 工具函数
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
cd backend
uvicorn api.main:app --reload --port 8000
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动前端服务

```bash
cd frontend
npm run dev
```

## 访问

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## API 端点

### Dashboard
- `GET /api/dashboard/stats` - 获取统计数据
- `GET /api/dashboard/phases/{project_id}` - 获取项目阶段进度

### Projects
- `GET /api/projects` - 列表
- `POST /api/projects` - 创建
- `GET /api/projects/{id}` - 详情
- `PATCH /api/projects/{id}` - 更新
- `DELETE /api/projects/{id}` - 删除

### Assets
- `GET /api/assets/papers` - 论文资产
- `GET /api/assets/code` - 代码资产
- `GET /api/assets/experiments` - 实验资产
- `GET /api/assets/graphs` - 图谱资产

### Alerts
- `GET /api/alerts` - 告警列表
- `POST /api/alerts` - 创建告警
- `PATCH /api/alerts/{id}` - 解决告警

### Reports
- `GET /api/reports` - 报告列表
- `POST /api/reports` - 生成报告

## 数据模型

1. **Project**: 项目 (id, name, current_phase, status, completion_ratio)
2. **StageRun**: 阶段运行 (id, project_id, stage_name, claimed_status, verified_status, completion_ratio)
3. **PaperAsset**: 论文资产 (id, paper_id, title, verdict, analysis_status, code_available)
4. **CodeAsset**: 代码资产 (id, repo_id, repo_url, stars, license, frameworks, reproducibility_status)
5. **ExperimentAsset**: 实验资产 (id, exp_id, project_id, status, metrics)
6. **GraphAsset**: 图谱资产 (id, project_id, node_count, edge_count, graph_type)
7. **Alert**: 告警 (id, alert_id, type, severity, message, is_resolved)
8. **Report**: 报告 (id, report_id, report_type, content, generated_at)
