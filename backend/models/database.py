from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    current_phase = Column(String(50), default="discovery")  # discovery, triage, analysis, synthesis, writing
    status = Column(String(50), default="idle")  # idle, running, paused, completed, error
    completion_ratio = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    stage_runs = relationship("StageRun", back_populates="project", cascade="all, delete-orphan")
    experiments = relationship("ExperimentAsset", back_populates="project", cascade="all, delete-orphan")
    graphs = relationship("GraphAsset", back_populates="project", cascade="all, delete-orphan")

class StageRun(Base):
    __tablename__ = "stage_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    stage_name = Column(String(50), nullable=False)  # discovery, triage, analysis, synthesis, writing
    claimed_status = Column(String(20), default="pending")  # pending, running, completed, failed
    verified_status = Column(String(20), default="unverified")  # unverified, verified, rejected
    completion_ratio = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="stage_runs")

class PaperAsset(Base):
    __tablename__ = "paper_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=True)
    venue = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    verdict = Column(String(20), nullable=True)  # reject, skim_only, deep_read, baseline
    analysis_status = Column(String(20), default="pending")  # pending, in_progress, completed, failed
    code_available = Column(Boolean, default=False)
    code_repo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CodeAsset(Base):
    __tablename__ = "code_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(String(100), unique=True, nullable=False, index=True)
    repo_url = Column(String(500), nullable=False)
    repo_name = Column(String(255), nullable=True)
    is_official = Column(Boolean, default=False)
    stars = Column(Integer, default=0)
    license = Column(String(100), nullable=True)
    frameworks = Column(Text, nullable=True)  # JSON string or comma-separated
    reproducibility_status = Column(String(20), default="unknown")  # unknown, reproducible, partially, not_reproducible
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExperimentAsset(Base):
    __tablename__ = "experiment_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    exp_id = Column(String(100), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    metrics = Column(Text, nullable=True)  # JSON string
    config = Column(Text, nullable=True)  # JSON string
    results_summary = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="experiments")

class GraphAsset(Base):
    __tablename__ = "graph_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    node_count = Column(Integer, default=0)
    edge_count = Column(Integer, default=0)
    last_update = Column(DateTime, default=datetime.utcnow)
    graph_type = Column(String(50), default="knowledge")  # knowledge, citation, experiment
    graph_metadata = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="graphs")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(100), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False)  # stage_blocked, cache_miss, asset_health, system
    severity = Column(String(20), nullable=False)  # info, warning, error, critical
    message = Column(Text, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(100), unique=True, nullable=False, index=True)
    report_type = Column(String(50), nullable=False)  # daily, weekly, monthly, custom
    title = Column(String(255), nullable=True, default="")
    content = Column(Text, nullable=False)  # JSON string
    generated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./research_os_monitor.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
