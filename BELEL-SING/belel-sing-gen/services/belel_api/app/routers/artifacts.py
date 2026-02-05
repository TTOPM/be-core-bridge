from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import FileResponse

from ..settings import settings
from ..core.paths import resolve_sandbox_root, resolve_under_root, ensure_exists, guess_media_type

router = APIRouter(tags=["artifacts"])


@router.get("/api/artifacts")
def get_artifact(path: str = Query(..., description="sandbox-relative path")):
    """
    Streams an artifact safely from under OUT_DIR.

    - WAV served with FileResponse (supports range requests via Starlette)
    - JSON served as application/json
    - .pt default is octet-stream (you should generally NOT fetch .pt in browser)
    """
    root = resolve_sandbox_root(settings.out_dir)
    p = resolve_under_root(root, path)
    ensure_exists(p)

    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_artifact_mb:
        raise HTTPException(status_code=413, detail="artifact too large")

    media_type = guess_media_type(p)
    return FileResponse(path=str(p), media_type=media_type, filename=p.name)
