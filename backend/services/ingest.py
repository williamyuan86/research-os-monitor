"""
ingest.py — Scan .research-os/ directories and populate the monitor DB.
Also provides Cytoscape-format graph data for the knowledge graph viewer.
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Root of .research-os/ project dirs
RESEARCH_OS_DIR = Path(
    os.getenv("RESEARCH_OS_DIR",
              str(Path.home() / ".openclaw/workspace/.research-os"))
)

# Fallback: pre-built UI data from research-os-ui
RESEARCH_UI_DATA_DIR = Path(
    os.getenv("RESEARCH_UI_DATA_DIR",
              str(Path.home() / ".openclaw/workspace/research-os-ui/data"))
)

# ── Skill → stage mapping ───────────────────────────────────────────

_SKILL_TO_STAGE = {
    "1.1-discovery":     "discovery",
    "1.2-triage":        "triage",
    "1.3-deep-analysis": "analysis",
    "2.1-knowledge-graph": "synthesis",
    "2.2-gap-finder":    "synthesis",
    "3-topic-assessor":  "synthesis",
    "4-experiment-plan": "writing",
    "5-paper-write":     "writing",
}

_PHASE_NUM_TO_STAGE = {
    "1": "analysis",
    "2": "synthesis",
    "3": "synthesis",
    "4": "writing",
    "5": "writing",
}

_STATE_TO_STATUS = {
    "EXPERIMENT_EXECUTING": "running",
    "WAITING_EXTERNAL_DATA": "running",
    "COMPLETE": "completed",
    "ERROR": "error",
    "PAUSED": "paused",
}


def _load_json(path: Path):
    """Load JSON file, return None on any error."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def scan_projects():
    """Return list of project slugs found in RESEARCH_OS_DIR."""
    if not RESEARCH_OS_DIR.exists():
        return []
    results = []
    for d in sorted(RESEARCH_OS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            results.append(d.name)
    return results


def get_project_info(project_slug: str) -> dict:
    """Return display metadata for a project slug."""
    proj_dir = RESEARCH_OS_DIR / project_slug
    state = _load_json(proj_dir / "pipeline-state.json") or {}
    display_name = (
        state.get("project_name")
        or state.get("name")
        or project_slug.replace("-", " ").replace("_", " ").title()
    )
    current_phase_raw = str(state.get("current_phase", "1")).split(".")[0]
    current_phase = _PHASE_NUM_TO_STAGE.get(current_phase_raw, "discovery")
    current_state = state.get("current_state", "")
    status = _STATE_TO_STATUS.get(current_state, "running")

    has_graph = bool(_find_kg_file(project_slug))
    return {
        "slug": project_slug,
        "name": display_name,
        "current_phase": current_phase,
        "status": status,
        "has_graph": has_graph,
    }


def ingest_project(project_slug: str, db):
    """
    Read skill output files for a project and upsert into the monitor DB.
    Returns the Project ORM instance, or None if the directory doesn't exist.
    """
    from models.database import (
        Project, StageRun, PaperAsset, GraphAsset
    )

    proj_dir = RESEARCH_OS_DIR / project_slug
    if not proj_dir.exists():
        return None

    # ── Pipeline state ──
    state = _load_json(proj_dir / "pipeline-state.json") or {}
    skill_outputs = state.get("skill_outputs", {})

    stage_status = {}
    for skill_key, skill_data in skill_outputs.items():
        stage = _SKILL_TO_STAGE.get(skill_key)
        if stage:
            s = skill_data.get("status", "pending")
            stage_status[stage] = "completed" if s in ("completed", "approved") else "running"

    stages = ["discovery", "triage", "analysis", "synthesis", "writing"]
    completed_count = sum(1 for s in stages if stage_status.get(s) == "completed")
    completion_ratio = completed_count / len(stages)

    current_phase_raw = str(state.get("current_phase", "1")).split(".")[0]
    current_phase = _PHASE_NUM_TO_STAGE.get(current_phase_raw, "discovery")
    current_state = state.get("current_state", "")
    status = _STATE_TO_STATUS.get(current_state, "running")

    # Infer phase/status from available files if state invalid
    outputs_dir = proj_dir / "outputs"
    if not skill_outputs and outputs_dir.exists():
        files = {f.name for f in outputs_dir.iterdir()}
        if any("knowledge-graph" in f or "knowledge_graph" in f for f in files):
            current_phase = "synthesis"
            completion_ratio = 0.6
        elif any("deep-analysis" in f or "deep_analysis" in f for f in files):
            current_phase = "analysis"
            completion_ratio = 0.4
        elif any("triage" in f for f in files):
            current_phase = "triage"
            completion_ratio = 0.2
        else:
            current_phase = "discovery"
            completion_ratio = 0.1

    # ── Upsert Project ──
    project = db.query(Project).filter(Project.name == project_slug).first()
    if not project:
        project = Project(
            name=project_slug,
            current_phase=current_phase,
            status=status,
            completion_ratio=completion_ratio,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
    else:
        project.current_phase = current_phase
        project.status = status
        project.completion_ratio = completion_ratio
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(project)

    # ── Upsert StageRuns ──
    for stage_name in stages:
        claimed = stage_status.get(stage_name, "pending")
        ratio = 1.0 if claimed == "completed" else 0.0
        stage_run = (
            db.query(StageRun)
            .filter(StageRun.project_id == project.id, StageRun.stage_name == stage_name)
            .first()
        )
        if not stage_run:
            stage_run = StageRun(
                project_id=project.id,
                stage_name=stage_name,
                claimed_status=claimed,
                completion_ratio=ratio,
            )
            db.add(stage_run)
        else:
            stage_run.claimed_status = claimed
            stage_run.completion_ratio = ratio
    db.commit()

    # ── Papers from triage ──
    triage_data = _load_triage(proj_dir)
    if triage_data:
        for p in triage_data:
            paper_id = p.get("paper_id", "")
            if not paper_id:
                continue
            existing = db.query(PaperAsset).filter(PaperAsset.paper_id == paper_id).first()
            if not existing:
                db.add(PaperAsset(
                    paper_id=paper_id,
                    title=p.get("title", paper_id),
                    authors=p.get("authors", ""),
                    venue=p.get("venue", ""),
                    verdict=p.get("verdict", "deep_read"),
                    analysis_status="pending",
                    code_available=False,
                ))
        db.commit()

    # ── Update analysis status from deep analysis ──
    analysis_data = _load_analysis(proj_dir)
    if analysis_data:
        for a in analysis_data:
            paper_id = a.get("paper_id", "")
            if not paper_id:
                continue
            existing = db.query(PaperAsset).filter(PaperAsset.paper_id == paper_id).first()
            if existing:
                existing.analysis_status = "completed"
            else:
                db.add(PaperAsset(
                    paper_id=paper_id,
                    title=a.get("title", paper_id),
                    analysis_status="completed",
                    verdict="deep_read",
                ))
        db.commit()

    # ── Graph asset ──
    cyto_data = get_cytoscape_graph(project_slug)
    if cyto_data:
        node_count = len(cyto_data.get("nodes", []))
        edge_count = len(cyto_data.get("edges", []))
        existing_graph = (
            db.query(GraphAsset)
            .filter(GraphAsset.project_id == project.id, GraphAsset.graph_type == "knowledge")
            .first()
        )
        if not existing_graph:
            db.add(GraphAsset(
                project_id=project.id,
                node_count=node_count,
                edge_count=edge_count,
                graph_type="knowledge",
            ))
        else:
            existing_graph.node_count = node_count
            existing_graph.edge_count = edge_count
            existing_graph.last_update = datetime.utcnow()
        db.commit()

    return project


# ── File loaders ────────────────────────────────────────────────────

def _load_triage(proj_dir: Path):
    """Return list of paper dicts from triage output, or None."""
    for fname in ("1.2-triage.json", "triage.json"):
        data = _load_json(proj_dir / "outputs" / fname)
        if data is None:
            continue
        papers = data.get("papers", [])
        if isinstance(papers, list) and papers:
            return papers
        # Some formats wrap papers differently
        if isinstance(data, list):
            return data
    return None


def _load_analysis(proj_dir: Path):
    """Return list of analysis dicts, or None."""
    for fname in ("1.3-deep-analysis.json", "deep_analysis.json"):
        data = _load_json(proj_dir / "outputs" / fname)
        if data is None:
            continue
        analyses = data.get("analyses", [])
        if isinstance(analyses, list) and analyses:
            return analyses
    return None


def _find_kg_file(project_slug: str):
    """
    Find a knowledge-graph file for a project. Returns (path, format) or None.
    format is one of: 'envelope', 'direct', 'cytoscape', 'embodied'
    """
    proj_dir = RESEARCH_OS_DIR / project_slug

    # 1) Skill output envelope format: output.knowledge_graph.nodes (dict)
    for fname in ("2.1-knowledge-graph.json",):
        p = proj_dir / "outputs" / fname
        if p.exists():
            return (p, "envelope")

    # 2) Direct graph format (no envelope wrapper)
    for fname in ("knowledge_graph.json", "knowledge-graph.json"):
        p = proj_dir / "outputs" / fname
        if p.exists():
            data = _load_json(p)
            if data:
                if isinstance(data.get("nodes"), list):
                    return (p, "cytoscape")
                return (p, "direct")

    # 3) Pre-built Cytoscape UI data (research-os-ui/data/)
    # Try exact slug, then slug without -phd suffix
    for candidate in (project_slug, project_slug.replace("-phd", "").replace("_phd", "")):
        p = RESEARCH_UI_DATA_DIR / f"{candidate}.json"
        if p.exists():
            return (p, "cytoscape")

    return None


# ── Cytoscape conversion ─────────────────────────────────────────────

def get_cytoscape_graph(project_slug: str):
    """
    Return Cytoscape-format dict {nodes, edges} for project_slug, or None.
    Handles multiple upstream formats automatically.
    """
    result = _find_kg_file(project_slug)
    if not result:
        return None
    path, fmt = result
    data = _load_json(path)
    if not data:
        return None

    if fmt == "cytoscape":
        # Already in UI format
        return data

    if fmt == "envelope":
        # { "output": { "knowledge_graph": { "nodes": {...}, "edges": [...] } } }
        graph = data.get("output", data).get("knowledge_graph", {})
        return _convert_standard_kg(graph)

    if fmt == "direct":
        # { "nodes": {...dict of type→list...}, "edges": [...] }
        # Could be standard dict format or embodied format with typed IDs
        nodes_raw = data.get("nodes", {})
        if isinstance(nodes_raw, dict):
            # Check if it's embodied-style (tasks/concepts instead of problems)
            has_embodied_types = any(k in nodes_raw for k in ("tasks", "concepts"))
            if has_embodied_types:
                return _convert_embodied_kg(data)
            else:
                return _convert_standard_kg(data)

    return None


def _convert_standard_kg(graph: dict) -> dict:
    """Convert knowledge-graph-builder standard format to Cytoscape."""
    nodes_raw = graph.get("nodes", {})
    edges_raw = graph.get("edges", [])

    if isinstance(nodes_raw, list):
        # Already Cytoscape nodes
        return {"nodes": nodes_raw, "edges": edges_raw}

    code_index = _build_code_index(graph)
    ui_nodes = []
    type_index = {}

    for paper in nodes_raw.get("papers", []):
        node = _convert_paper(paper, code_index)
        ui_nodes.append(node)
        type_index[paper["id"]] = "paper"

    for method in nodes_raw.get("methods", []):
        node = _convert_entity(method, "method")
        ui_nodes.append(node)
        type_index[method["id"]] = "method"

    for problem in nodes_raw.get("problems", []):
        node = _convert_entity(problem, "problem")
        ui_nodes.append(node)
        type_index[problem["id"]] = "problem"

    for dataset in nodes_raw.get("datasets", []):
        node = _convert_entity(dataset, "dataset")
        ui_nodes.append(node)
        type_index[dataset["id"]] = "dataset"

    for metric in nodes_raw.get("metrics", []):
        node = _convert_entity(metric, "metric")
        ui_nodes.append(node)
        type_index[metric["id"]] = "metric"

    ui_edges = _convert_edges(edges_raw, type_index)
    return {"nodes": ui_nodes, "edges": ui_edges}


def _convert_embodied_kg(graph: dict) -> dict:
    """Convert embodied-action-pomdp style KG to Cytoscape (different node types)."""
    nodes_raw = graph.get("nodes", {})
    edges_raw = graph.get("edges", [])

    ui_nodes = []
    type_index = {}

    # Type mapping for non-standard node categories
    type_map = {
        "methods": "method",
        "papers": "paper",
        "datasets": "dataset",
        "tasks": "problem",      # tasks → problem
        "concepts": "method",    # concepts → method (closest)
        "metrics": "metric",
    }

    for category, ui_type in type_map.items():
        for node in nodes_raw.get(category, []):
            nid = node.get("id", "")
            if not nid:
                continue
            if ui_type == "paper":
                # Build paper node
                title = node.get("title") or node.get("name") or nid
                arXiv = node.get("arXiv")
                url = f"https://arxiv.org/abs/{arXiv}" if arXiv else None
                pdf = f"https://arxiv.org/pdf/{arXiv}" if arXiv else None
                label = _make_label(nid, title)
                ui_nodes.append({"data": {
                    "id": nid,
                    "type": "paper",
                    "label": label,
                    "title": title,
                    "venue": node.get("venue"),
                    "year": node.get("year"),
                    "topic": node.get("core_contribution") or node.get("topic"),
                    "abstract": node.get("abstract") or node.get("description"),
                    "url": url,
                    "pdf": pdf,
                    "code": None,
                }})
            else:
                name = node.get("name") or nid
                desc = node.get("description") or node.get("desc")
                label = _make_label(nid, name)
                ui_nodes.append({"data": {
                    "id": nid,
                    "type": ui_type,
                    "label": label,
                    "name": name,
                    "desc": desc,
                }})
            type_index[nid] = ui_type

    # Edge relation map for embodied format
    edge_remap = {
        "contains": "uses",
        "enables": "uses",
        "applied_to": "solves",
        "uses": "uses",
        "extends": "extends",
        "benchmarks_on": "evaluated_on",
        "evaluates": "evaluated_on",
        "demonstrates": "uses",
    }

    ui_edges = []
    for e in edges_raw:
        src = e.get("source", "")
        tgt = e.get("target", "")
        rel = e.get("relation", "")
        if not src or not tgt:
            continue
        # Skip unknown node references
        if src not in type_index or tgt not in type_index:
            continue
        ui_rel = edge_remap.get(rel, rel)
        ui_edges.append({"data": {"source": src, "target": tgt, "type": ui_rel}})

    return {"nodes": ui_nodes, "edges": ui_edges}


# ── Helpers ──────────────────────────────────────────────────────────

def _make_label(node_id: str, name: str, max_len: int = 20) -> str:
    short = name[:max_len] + "…" if len(name) > max_len else name
    return f"{node_id}: {short}"


def _build_code_index(graph: dict) -> dict:
    """Build {paper_id: repo_url} from released_with edges."""
    repo_map = {r["id"]: r for r in graph.get("code_repos", []) if "id" in r}
    index = {}
    for edge in graph.get("edges", []):
        if edge.get("relation") != "released_with":
            continue
        paper_id = edge.get("source")
        repo_id = edge.get("target")
        repo = repo_map.get(repo_id)
        if repo and repo.get("official") and repo.get("repo_url"):
            index[paper_id] = repo["repo_url"]
    return index


def _convert_paper(p: dict, code_index: dict) -> dict:
    pid = p["id"]
    title = p.get("title") or p.get("name") or pid
    abstract = p.get("abstract_zh") or p.get("abstract_cn") or p.get("abstract")
    url = p.get("url") or p.get("arxiv_url") or p.get("link")
    pdf = p.get("pdf") or p.get("pdf_url")
    code = code_index.get(pid)
    return {"data": {
        "id": pid,
        "type": "paper",
        "label": _make_label(pid, title),
        "title": title,
        "venue": p.get("venue"),
        "year": p.get("year"),
        "topic": p.get("family") or p.get("topic") or p.get("innovation_type"),
        "abstract": abstract,
        "url": url,
        "pdf": pdf,
        "code": code,
    }}


def _convert_entity(node: dict, node_type: str) -> dict:
    nid = node["id"]
    name = node.get("name") or node.get("label") or nid
    desc = node.get("description") or node.get("desc")
    return {"data": {
        "id": nid,
        "type": node_type,
        "label": _make_label(nid, name),
        "name": name,
        "desc": desc,
    }}


_EDGE_TYPE_MAP = {
    "uses": "uses",
    "solves": "solves",
    "evaluated_on": "evaluated_on",
    "extends": "extends",
    "competes_with": "competes_with",
    "cites": "cites",
}

_RETYPE_BY_TARGET = {
    "dataset": "uses_dataset",
    "metric": "measures",
}

_SKIP_RELATIONS = {"released_with", "implements", "supports_framework"}


def _convert_edges(edges: list, type_index: dict) -> list:
    result = []
    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        rel = e.get("relation", "")
        if not src or not tgt:
            continue
        if rel in _SKIP_RELATIONS:
            continue
        if rel == "uses":
            tgt_type = type_index.get(tgt, "")
            rel = _RETYPE_BY_TARGET.get(tgt_type, "uses")
        ui_type = _EDGE_TYPE_MAP.get(rel, rel)
        result.append({"data": {"source": src, "target": tgt, "type": ui_type}})
    return result
