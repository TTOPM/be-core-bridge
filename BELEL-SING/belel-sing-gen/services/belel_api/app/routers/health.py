from __future__ import annotations

from fastapi import APIRouter
from datetime import datetime, timezone

from ..settings import settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "belel_api",
        "build_id": settings.build_id,
        "utc": datetime.now(timezone.utc).isoformat()
    }
