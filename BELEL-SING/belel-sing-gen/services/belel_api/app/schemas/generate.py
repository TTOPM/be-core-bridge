from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str
    lyrics: str = ""
    duration_sec: int = Field(ge=1, le=600)
    language: str = "en"
    steps: Optional[int] = Field(default=None, ge=1, le=50)
    guidance: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    seed: Optional[int] = None
    codec_ckpt: Optional[str] = None
    denoiser_ckpt: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class BenchmarkBlock(BaseModel):
    score_10: float
    passed: bool
    breakdown: Optional[Dict[str, Any]] = None
    alignment_pending: Optional[bool] = None
    gate_failures: Optional[Dict[str, Any]] = None


class GenerateResponse(BaseModel):
    project_id: str
    version_id: str
    wav_path: str
    mel_path: str
    wav_sidecar: str
    meta: Optional[Dict[str, Any]] = None
    benchmark: Optional[BenchmarkBlock] = None
