from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Project schemas
class ProjectBase(BaseModel):
    name: str
    current_phase: str = "discovery"
    status: str = "idle"
    completion_ratio: float = 0.0

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    current_phase: Optional[str] = None
    status: Optional[str] = None
    completion_ratio: Optional[float] = None

class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# StageRun schemas
class StageRunBase(BaseModel):
    stage_name: str
    claimed_status: str = "pending"
    verified_status: str = "unverified"
    completion_ratio: float = 0.0

class StageRunCreate(StageRunBase):
    project_id: int

class StageRunUpdate(BaseModel):
    claimed_status: Optional[str] = None
    verified_status: Optional[str] = None
    completion_ratio: Optional[float] = None
    error_message: Optional[str] = None

class StageRunResponse(StageRunBase):
    id: int
    project_id: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# PaperAsset schemas
class PaperAssetBase(BaseModel):
    paper_id: str
    title: str
    authors: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    verdict: Optional[str] = None
    analysis_status: str = "pending"
    code_available: bool = False
    code_repo_url: Optional[str] = None

class PaperAssetCreate(PaperAssetBase):
    pass

class PaperAssetUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    verdict: Optional[str] = None
    analysis_status: Optional[str] = None
    code_available: Optional[bool] = None
    code_repo_url: Optional[str] = None

class PaperAssetResponse(PaperAssetBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# CodeAsset schemas
class CodeAssetBase(BaseModel):
    repo_id: str
    repo_url: str
    repo_name: Optional[str] = None
    is_official: bool = False
    stars: int = 0
    license: Optional[str] = None
    frameworks: Optional[str] = None
    reproducibility_status: str = "unknown"

class CodeAssetCreate(CodeAssetBase):
    pass

class CodeAssetUpdate(BaseModel):
    repo_url: Optional[str] = None
    repo_name: Optional[str] = None
    is_official: Optional[bool] = None
    stars: Optional[int] = None
    license: Optional[str] = None
    frameworks: Optional[str] = None
    reproducibility_status: Optional[str] = None

class CodeAssetResponse(CodeAssetBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ExperimentAsset schemas
class ExperimentAssetBase(BaseModel):
    exp_id: str
    project_id: int
    status: str = "pending"
    metrics: Optional[str] = None
    config: Optional[str] = None
    results_summary: Optional[str] = None

class ExperimentAssetCreate(ExperimentAssetBase):
    pass

class ExperimentAssetUpdate(BaseModel):
    status: Optional[str] = None
    metrics: Optional[str] = None
    config: Optional[str] = None
    results_summary: Optional[str] = None

class ExperimentAssetResponse(ExperimentAssetBase):
    id: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# GraphAsset schemas
class GraphAssetBase(BaseModel):
    project_id: int
    node_count: int = 0
    edge_count: int = 0
    graph_type: str = "knowledge"
    graph_metadata: Optional[str] = None

class GraphAssetCreate(GraphAssetBase):
    pass

class GraphAssetUpdate(BaseModel):
    node_count: Optional[int] = None
    edge_count: Optional[int] = None
    graph_type: Optional[str] = None
    graph_metadata: Optional[str] = None

class GraphAssetResponse(GraphAssetBase):
    id: int
    last_update: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

# Alert schemas
class AlertBase(BaseModel):
    alert_id: str
    type: str
    severity: str
    message: str
    project_id: Optional[int] = None

class AlertCreate(AlertBase):
    pass

class AlertUpdate(BaseModel):
    is_resolved: Optional[bool] = None

class AlertResponse(AlertBase):
    id: int
    is_resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Report schemas
class ReportBase(BaseModel):
    report_id: str
    report_type: str
    title: str
    content: str

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: int
    generated_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True
class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    total_papers: int
    papers_analyzed: int
    total_code_assets: int
    total_experiments: int
    experiments_completed: int
    active_alerts: int
    critical_alerts: int

class PhaseProgress(BaseModel):
    phase: str
    progress: float
    status: str
