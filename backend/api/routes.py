from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.database import get_db, Project, StageRun, PaperAsset, CodeAsset, ExperimentAsset, GraphAsset, Alert, Report
from models.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    StageRunCreate, StageRunUpdate, StageRunResponse,
    PaperAssetCreate, PaperAssetUpdate, PaperAssetResponse,
    CodeAssetCreate, CodeAssetUpdate, CodeAssetResponse,
    ExperimentAssetCreate, ExperimentAssetUpdate, ExperimentAssetResponse,
    GraphAssetCreate, GraphAssetUpdate, GraphAssetResponse,
    AlertCreate, AlertUpdate, AlertResponse,
    ReportCreate, ReportResponse,
    DashboardStats, PhaseProgress
)

router = APIRouter()

# ============= Dashboard =============
@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(Project.status == "running").count()
    completed_projects = db.query(Project).filter(Project.status == "completed").count()
    
    total_papers = db.query(PaperAsset).count()
    papers_analyzed = db.query(PaperAsset).filter(PaperAsset.analysis_status == "completed").count()
    
    total_code_assets = db.query(CodeAsset).count()
    
    total_experiments = db.query(ExperimentAsset).count()
    experiments_completed = db.query(ExperimentAsset).filter(ExperimentAsset.status == "completed").count()
    
    active_alerts = db.query(Alert).filter(Alert.is_resolved == False).count()
    critical_alerts = db.query(Alert).filter(Alert.is_resolved == False, Alert.severity == "critical").count()
    
    return DashboardStats(
        total_projects=total_projects,
        active_projects=active_projects,
        completed_projects=completed_projects,
        total_papers=total_papers,
        papers_analyzed=papers_analyzed,
        total_code_assets=total_code_assets,
        total_experiments=total_experiments,
        experiments_completed=experiments_completed,
        active_alerts=active_alerts,
        critical_alerts=critical_alerts
    )

@router.get("/dashboard/phases/{project_id}", response_model=List[PhaseProgress])
def get_project_phases(project_id: int, db: Session = Depends(get_db)):
    stages = db.query(StageRun).filter(StageRun.project_id == project_id).all()
    phases = ["discovery", "triage", "analysis", "synthesis", "writing"]
    
    result = []
    for phase in phases:
        stage = next((s for s in stages if s.stage_name == phase), None)
        if stage:
            result.append(PhaseProgress(
                phase=phase,
                progress=stage.completion_ratio,
                status=stage.claimed_status
            ))
        else:
            result.append(PhaseProgress(phase=phase, progress=0.0, status="pending"))
    
    return result

# ============= Projects =============
@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return db.query(Project).offset(skip).limit(limit).all()

@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/projects", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Create stage runs for all phases
    phases = ["discovery", "triage", "analysis", "synthesis", "writing"]
    for phase in phases:
        stage_run = StageRun(project_id=db_project.id, stage_name=phase)
        db.add(stage_run)
    db.commit()
    
    return db_project

@router.patch("/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project: ProjectUpdate, db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for key, value in project.model_dump(exclude_unset=True).items():
        setattr(db_project, key, value)
    db_project.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_project)
    return db_project

@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}

# ============= Stage Runs =============
@router.get("/projects/{project_id}/stages", response_model=List[StageRunResponse])
def list_stages(project_id: int, db: Session = Depends(get_db)):
    return db.query(StageRun).filter(StageRun.project_id == project_id).all()

@router.post("/projects/{project_id}/stages", response_model=StageRunResponse)
def create_stage(project_id: int, stage: StageRunCreate, db: Session = Depends(get_db)):
    db_stage = StageRun(**stage.model_dump())
    db.add(db_stage)
    db.commit()
    db.refresh(db_stage)
    return db_stage

@router.patch("/stages/{stage_id}", response_model=StageRunResponse)
def update_stage(stage_id: int, stage: StageRunUpdate, db: Session = Depends(get_db)):
    db_stage = db.query(StageRun).filter(StageRun.id == stage_id).first()
    if not db_stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    for key, value in stage.model_dump(exclude_unset=True).items():
        setattr(db_stage, key, value)
    
    if stage.claimed_status == "completed" and not db_stage.completed_at:
        db_stage.completed_at = datetime.utcnow()
    elif stage.claimed_status == "running" and not db_stage.started_at:
        db_stage.started_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_stage)
    return db_stage

# ============= Paper Assets =============
@router.get("/assets/papers", response_model=List[PaperAssetResponse])
def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    verdict: Optional[str] = None,
    analysis_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(PaperAsset)
    if verdict:
        query = query.filter(PaperAsset.verdict == verdict)
    if analysis_status:
        query = query.filter(PaperAsset.analysis_status == analysis_status)
    return query.offset(skip).limit(limit).all()

@router.get("/assets/papers/{paper_id}", response_model=PaperAssetResponse)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(PaperAsset).filter(PaperAsset.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper

@router.post("/assets/papers", response_model=PaperAssetResponse)
def create_paper(paper: PaperAssetCreate, db: Session = Depends(get_db)):
    db_paper = PaperAsset(**paper.model_dump())
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper

@router.patch("/assets/papers/{paper_id}", response_model=PaperAssetResponse)
def update_paper(paper_id: int, paper: PaperAssetUpdate, db: Session = Depends(get_db)):
    db_paper = db.query(PaperAsset).filter(PaperAsset.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    for key, value in paper.model_dump(exclude_unset=True).items():
        setattr(db_paper, key, value)
    
    db.commit()
    db.refresh(db_paper)
    return db_paper

@router.delete("/assets/papers/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(PaperAsset).filter(PaperAsset.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    db.delete(paper)
    db.commit()
    return {"message": "Paper deleted"}

# ============= Code Assets =============
@router.get("/assets/code", response_model=List[CodeAssetResponse])
def list_code_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return db.query(CodeAsset).offset(skip).limit(limit).all()

@router.get("/assets/code/{repo_id}", response_model=CodeAssetResponse)
def get_code_asset(repo_id: int, db: Session = Depends(get_db)):
    code = db.query(CodeAsset).filter(CodeAsset.id == repo_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code asset not found")
    return code

@router.post("/assets/code", response_model=CodeAssetResponse)
def create_code_asset(code: CodeAssetCreate, db: Session = Depends(get_db)):
    db_code = CodeAsset(**code.model_dump())
    db.add(db_code)
    db.commit()
    db.refresh(db_code)
    return db_code

@router.patch("/assets/code/{repo_id}", response_model=CodeAssetResponse)
def update_code_asset(repo_id: int, code: CodeAssetUpdate, db: Session = Depends(get_db)):
    db_code = db.query(CodeAsset).filter(CodeAsset.id == repo_id).first()
    if not db_code:
        raise HTTPException(status_code=404, detail="Code asset not found")
    
    for key, value in code.model_dump(exclude_unset=True).items():
        setattr(db_code, key, value)
    
    db.commit()
    db.refresh(db_code)
    return db_code

@router.delete("/assets/code/{repo_id}")
def delete_code_asset(repo_id: int, db: Session = Depends(get_db)):
    code = db.query(CodeAsset).filter(CodeAsset.id == repo_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code asset not found")
    
    db.delete(code)
    db.commit()
    return {"message": "Code asset deleted"}

# ============= Experiment Assets =============
@router.get("/assets/experiments", response_model=List[ExperimentAssetResponse])
def list_experiments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ExperimentAsset)
    if project_id:
        query = query.filter(ExperimentAsset.project_id == project_id)
    return query.offset(skip).limit(limit).all()

@router.get("/assets/experiments/{exp_id}", response_model=ExperimentAssetResponse)
def get_experiment(exp_id: int, db: Session = Depends(get_db)):
    exp = db.query(ExperimentAsset).filter(ExperimentAsset.id == exp_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp

@router.post("/assets/experiments", response_model=ExperimentAssetResponse)
def create_experiment(exp: ExperimentAssetCreate, db: Session = Depends(get_db)):
    db_exp = ExperimentAsset(**exp.model_dump())
    db.add(db_exp)
    db.commit()
    db.refresh(db_exp)
    return db_exp

@router.patch("/assets/experiments/{exp_id}", response_model=ExperimentAssetResponse)
def update_experiment(exp_id: int, exp: ExperimentAssetUpdate, db: Session = Depends(get_db)):
    db_exp = db.query(ExperimentAsset).filter(ExperimentAsset.id == exp_id).first()
    if not db_exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    for key, value in exp.model_dump(exclude_unset=True).items():
        setattr(db_exp, key, value)
    
    if exp.status == "completed" and not db_exp.completed_at:
        db_exp.completed_at = datetime.utcnow()
    elif exp.status == "running" and not db_exp.started_at:
        db_exp.started_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_exp)
    return db_exp

# ============= Graph Assets =============
@router.get("/assets/graphs", response_model=List[GraphAssetResponse])
def list_graphs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(GraphAsset)
    if project_id:
        query = query.filter(GraphAsset.project_id == project_id)
    return query.offset(skip).limit(limit).all()

@router.get("/assets/graphs/{graph_id}", response_model=GraphAssetResponse)
def get_graph(graph_id: int, db: Session = Depends(get_db)):
    graph = db.query(GraphAsset).filter(GraphAsset.id == graph_id).first()
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    return graph

@router.post("/assets/graphs", response_model=GraphAssetResponse)
def create_graph(graph: GraphAssetCreate, db: Session = Depends(get_db)):
    db_graph = GraphAsset(**graph.model_dump())
    db.add(db_graph)
    db.commit()
    db.refresh(db_graph)
    return db_graph

@router.patch("/assets/graphs/{graph_id}", response_model=GraphAssetResponse)
def update_graph(graph_id: int, graph: GraphAssetUpdate, db: Session = Depends(get_db)):
    db_graph = db.query(GraphAsset).filter(GraphAsset.id == graph_id).first()
    if not db_graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    for key, value in graph.model_dump(exclude_unset=True).items():
        setattr(db_graph, key, value)
    db_graph.last_update = datetime.utcnow()
    
    db.commit()
    db.refresh(db_graph)
    return db_graph

# ============= Alerts =============
@router.get("/alerts", response_model=List[AlertResponse])
def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if resolved is not None:
        query = query.filter(Alert.is_resolved == resolved)
    if severity:
        query = query.filter(Alert.severity == severity)
    return query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/alerts", response_model=AlertResponse)
def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    db_alert = Alert(**alert.model_dump())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
def resolve_alert(alert_id: int, alert: AlertUpdate, db: Session = Depends(get_db)):
    db_alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.is_resolved is not None:
        db_alert.is_resolved = alert.is_resolved
        if alert.is_resolved:
            db_alert.resolved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    db.delete(alert)
    db.commit()
    return {"message": "Alert deleted"}

# ============= Reports =============
@router.get("/reports", response_model=List[ReportResponse])
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    report_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Report)
    if report_type:
        query = query.filter(Report.report_type == report_type)
    return query.order_by(Report.generated_at.desc()).offset(skip).limit(limit).all()

@router.post("/reports", response_model=ReportResponse)
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    db_report = Report(**report.model_dump())
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

# ============= Ingest (disk → DB) =============

@router.get("/ingest/scan")
def scan_projects():
    """List all project slugs found in .research-os/ directory."""
    from services.ingest import scan_projects as _scan, get_project_info
    slugs = _scan()
    return {"projects": [get_project_info(s) for s in slugs]}

@router.post("/ingest/{project_slug}")
def ingest_one_project(project_slug: str, db: Session = Depends(get_db)):
    """Ingest a single project from .research-os/{project_slug}/."""
    from services.ingest import ingest_project as _ingest
    project = _ingest(project_slug, db)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found in .research-os/")
    return {"message": f"Ingested: {project.name}", "project_id": project.id}

@router.post("/ingest/auto/all")
def auto_ingest_all(db: Session = Depends(get_db)):
    """Scan and ingest all projects from .research-os/."""
    from services.ingest import scan_projects as _scan, ingest_project as _ingest
    ingested = []
    errors = []
    for slug in _scan():
        try:
            project = _ingest(slug, db)
            if project:
                ingested.append(project.name)
        except Exception as e:
            errors.append({"slug": slug, "error": str(e)})
    return {"ingested": ingested, "errors": errors, "count": len(ingested)}

# ============= Knowledge Graph Viewer =============

@router.get("/graphs/knowledge/{project_slug}")
def get_knowledge_graph_data(project_slug: str):
    """Return Cytoscape-format knowledge graph for a project."""
    from services.ingest import get_cytoscape_graph
    data = get_cytoscape_graph(project_slug)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No knowledge graph found for '{project_slug}'")
    return data
