from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from ..schemas.generate import GenerateRequest, GenerateResponse, BenchmarkBlock
from ..settings import settings
from ..core.engine_singleton import get_engine
from ..core.paths import resolve_sandbox_root
from ..storage.project_index import ProjectIndex

router = APIRouter(tags=["generate"])


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    """
    Calls BelelHyperEngine and persists project/version to index.

    This endpoint is deterministic only insofar as your engine is deterministic
    given seed + params; UI will display receipts only after edits.
    """
    engine = get_engine()
    root = resolve
