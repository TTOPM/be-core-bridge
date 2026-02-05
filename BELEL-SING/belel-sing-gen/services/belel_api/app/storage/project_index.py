from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import orjson

from .locks import lock_for


@dataclass
class ProjectIndex:
    """
    Simple JSON index for library + version tracking.

    Shape (stored):
    {
      "projects": {
        "<project_id>": {
          "project_id": "...",
          "title": "...",
          "created_utc": "...",
          "updated_utc": "...",
          "active_version_id": "v0",
          "versions": [
            {
              "version_id": "v0",
              "utc": "...",
              "wav_path": "...",
              "mel_path": "...",
              "wav_sidecar": "...",
              "receipt": "...",
              "edit_id": "...",
              "edit_type": "...",
              "benchmark": {...},
              "meta": {...},
              "committed": false
            }
          ]
        }
      }
    }
    """

    path: Path

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> Dict[str, Any]:
        self._ensure_parent()
        if not self.path.exists():
            return {"projects": {}}
        raw = self.path.read_bytes()
        if not raw:
            return {"projects": {}}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            # fallback: try orjson
            return orjson.loads(raw)

    def write(self, data: Dict[str, Any]) -> None:
        self._ensure_parent()
        b = orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
        self.path.write_bytes(b)

    def upsert_project(self, project_id: str, title: str, utc: str) -> None:
        with lock_for(self.path):
            data = self.read()
            projects = data.setdefault("projects", {})
            prj = projects.get(project_id)
            if prj is None:
                projects[project_id] = {
                    "project_id": project_id,
                    "title": title,
                    "created_utc": utc,
                    "updated_utc": utc,
                    "active_version_id": None,
                    "versions": []
                }
            else:
                prj["title"] = title
                prj["updated_utc"] = utc
            self.write(data)

    def append_version(self, project_id: str, version: Dict[str, Any], set_active: bool = True) -> None:
        with lock_for(self.path):
            data = self.read()
            prj = data.setdefault("projects", {}).setdefault(
                project_id,
                {
                    "project_id": project_id,
                    "title": version.get("title", "Untitled"),
                    "created_utc": version.get("utc"),
                    "updated_utc": version.get("utc"),
                    "active_version_id": None,
                    "versions": []
                },
            )
            prj["updated_utc"] = version.get("utc")
            prj.setdefault("versions", []).append(version)
            if set_active:
                prj["active_version_id"] = version.get("version_id")
            self.write(data)

    def set_active(self, project_id: str, version_id: str, utc: str) -> None:
        with lock_for(self.path):
            data = self.read()
            prj = data.setdefault("projects", {}).get(project_id)
            if prj is None:
                return
            prj["active_version_id"] = version_id
            prj["updated_utc"] = utc
            self.write(data)

    def list_projects(self) -> List[Dict[str, Any]]:
        data = self.read()
        out: List[Dict[str, Any]] = []
        for _, prj in (data.get("projects") or {}).items():
            out.append(
                {
                    "project_id": prj.get("project_id"),
                    "title": prj.get("title"),
                    "created_utc": prj.get("created_utc"),
                    "updated_utc": prj.get("updated_utc"),
                    "active_version_id": prj.get("active_version_id"),
                    "version_count": len(prj.get("versions") or []),
                }
            )
        out.sort(key=lambda x: x.get("updated_utc") or "", reverse=True)
        return out

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        data = self.read()
        return (data.get("projects") or {}).get(project_id)

    def find_version(self, project_id: str, version_id: str) -> Optional[Dict[str, Any]]:
        prj = self.get_project(project_id)
        if not prj:
            return None
        for v in prj.get("versions") or []:
            if v.get("version_id") == version_id:
                return v
        return None
