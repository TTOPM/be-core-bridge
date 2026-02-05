from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..schemas.project import ProjectsResponse, ProjectDetail
from ..settings import settings
from ..core.paths import resolve_sandbox_root
from ..storage.project_index import ProjectIndex

router = APIRouter(tags=["projects"])


def _index() -> ProjectIndex:
    root = resolve_sandbox_root(settings.out_dir)
    idx_path = (root / settings.project_index_relpath).resolve()
    return ProjectIndex(idx_path)


@router.get("/api/projects", response_model=ProjectsResponse)
def list_projects():
    idx = _index()
    projects = idx.list_projects()
    return {"projects": projects}


@router.get("/api/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str):
    idx = _index()
    prj = idx.get_project(project_id)
    if not prj:
        raise HTTPException(status_code=404, detail="project not found")
    return prj
