from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routes import router
from models.database import init_db, get_db

app = FastAPI(
    title="Research OS Monitor API",
    description="Backend API for Research OS workflow monitoring and asset management",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Auto-ingest any existing .research-os/ projects
    try:
        from services.ingest import scan_projects, ingest_project
        db = next(get_db())
        try:
            for slug in scan_projects():
                ingest_project(slug, db)
        finally:
            db.close()
    except Exception as e:
        print(f"[startup] Auto-ingest warning: {e}")

# Include routers
app.include_router(router, prefix="/api", tags=["research-os"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "research-os-monitor"}

