from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..settings import settings
from ..core.paths import resolve_sandbox_root, resolve_under_root, ensure_exists
from ..schemas.receipt import ReceiptResponse
from ..storage.project_index import ProjectIndex

router = APIRouter(tags=["receipt"])


@router.get("/api/receipt/{project_id}/{version_id}", response_model=ReceiptResponse)
def get_receipt(project_id: str, version_id: str):
    root = resolve_sandbox_root(settings.out_dir)
    idx = ProjectIndex((root / settings.project_index_relpath).resolve())
    ver = idx.find_version(project_id, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="version not found")
    receipt_path = ver.get("receipt")
    if not receipt_path:
        raise HTTPException(status_code=404, detail="receipt not recorded for this version")

    p = resolve_under_root(root, receipt_path)
    ensure_exists(p)

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to parse receipt json: {e}")

    return ReceiptResponse(receipt=data)
