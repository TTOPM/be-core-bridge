from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ProjectSummary(BaseModel):
    project_id: str
    title: str
    created_utc: Optional[str] = None
    updated_utc: Optional[str] = None
    active_version_id: Optional[str] = None
    version_count: int


class ProjectsResponse(BaseModel):
    projects: List[ProjectSummary]


class ProjectDetail(BaseModel):
    project_id: str
    title: str
    created_utc: Optional[str] = None
    updated_utc: Optional[str] = None
    active_version_id: Optional[str] = None
    versions: List[Dict[str, Any]]
