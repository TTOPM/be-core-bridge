from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class PerfLatestResponse(BaseModel):
    utc: str
    device: str
    dtype: str
    steps: int
    duration_sec: int
    e2e_sec: float
    codec_ckpt: Optional[str] = None
    denoiser_ckpt: Optional[str] = None
    claim: str
    raw: Optional[Dict[str, Any]] = None
