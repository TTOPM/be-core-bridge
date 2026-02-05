from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


EditType = Literal["repaint", "extend", "retake", "lyric_edit"]


class EditRequest(BaseModel):
    edit_type: EditType

    # paths (sandbox-relative preferred)
    src_mel_pt: str
    src_wav: Optional[str] = None

    prompt_override: Optional[str] = None
    lyrics_override: Optional[str] = None

    start_sec: Optional[float] = None
    end_sec: Optional[float] = None
    extend_sec: Optional[float] = None

    strength: float = Field(ge=0.0, le=1.0)
    seed_delta: int = 0
    attempt: int = 0

    steps_override: Optional[int] = Field(default=None, ge=1, le=50)
    guidance_override: Optional[float] = Field(default=None, ge=0.0, le=50.0)

    extra: Optional[Dict[str, Any]] = None


class BenchmarkBlock(BaseModel):
    score_10: float
    passed: bool
    breakdown: Optional[Dict[str, Any]] = None
    alignment_pending: Optional[bool] = None
    gate_failures: Optional[Dict[str, Any]] = None


class EditResponse(BaseModel):
    project_id: str
    version_id: str
    wav_path: str
    mel_path: str
    wav_sidecar: str
    receipt: str

    edit_id: str
    edit_type: str

    benchmark: Optional[BenchmarkBlock] = None
    meta: Optional[Dict[str, Any]] = None
