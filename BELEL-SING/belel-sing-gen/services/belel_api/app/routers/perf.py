from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

from ..settings import settings
from ..schemas.perf import PerfLatestResponse
from ..core.paths import resolve_sandbox_root, resolve_under_root

router = APIRouter(tags=["perf"])


@router.get("/api/perf/latest", response_model=PerfLatestResponse)
def perf_latest():
    """
    Reads latest perf claim output written by your belel_perf_claim_runner.py.

    Convention:
      outputs/perf/latest.json (sandbox-relative)
    You can change this to whatever your runner writes; keep it deterministic and single-source.
    """
    root = resolve_sandbox_root(settings.out_dir)
    candidate = root / "perf" / "latest.json"
    if not candidate.exists():
        # Return an explicit empty-but-valid object (UI expects shape)
        utc = datetime.now(timezone.utc).isoformat()
        return PerfLatestResponse(
            utc=utc,
            device="unknown",
            dtype="unknown",
            steps=0,
            duration_sec=0,
            e2e_sec=0.0,
            claim="",
            raw={}
        )

    data = json.loads(candidate.read_text(encoding="utf-8"))
    return PerfLatestResponse(
        utc=data.get("utc") or datetime.now(timezone.utc).isoformat(),
        device=data.get("device") or "unknown",
        dtype=data.get("dtype") or "unknown",
        steps=int(data.get("steps") or 0),
        duration_sec=int(data.get("duration_sec") or 0),
        e2e_sec=float(data.get("e2e_sec") or 0.0),
        codec_ckpt=data.get("codec_ckpt"),
        denoiser_ckpt=data.get("denoiser_ckpt"),
        claim=data.get("claim") or "",
        raw=data.get("raw") or data
    )
