# BELEL-SING/belel-sing-gen/belel_edit_suite/app.py
from __future__ import annotations

import os
import json
import time
import shutil
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

import torch

# FastAPI (UI + API)
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# BELEL core
from belel_hyper_core.belel_engine import BelelHyperEngine, BelelHyperConfig, BelelHyperRequest
from belel_hyper_core.editing.belel_editing import (
    BelelEditMode,
    BelelEditRequest,
    BelelEditingPipeline,
)
from belel_hyper_core.lang.belel_language_pack import (
    BELEL_LANGUAGES,
    normalize_text_for_language,
)


APP_ROOT = Path(__file__).resolve().parent
STATIC_DIR = APP_ROOT / "static"
JOBS_DIR = APP_ROOT / "jobs"


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_float(x: str, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _safe_int(x: str, default: int) -> int:
    try:
        return int(float(x))
    except Exception:
        return int(default)


def _job_id() -> str:
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    return f"job_{ts}_{os.getpid()}"


def _copy_into_job(job_dir: Path, src: Path) -> Path:
    dst = job_dir / src.name
    shutil.copy2(str(src), str(dst))
    return dst


def _resolve_engine_from_env() -> BelelHyperEngine:
    """
    Uses environment variables so you can run the edit suite without changing code.

    Required:
      BELEL_CODEC_CKPT
      BELEL_DENOISER_CKPT

    Optional:
      BELEL_DEVICE (default: cuda)
      BELEL_DTYPE (default: float16)
      BELEL_OUT_DIR (default: outputs/belel_edit_suite)
      BELEL_GUIDANCE (default: 6.0)
      BELEL_SEED (default: none)
    """
    codec_ckpt = os.environ.get("BELEL_CODEC_CKPT", "").strip()
    denoiser_ckpt = os.environ.get("BELEL_DENOISER_CKPT", "").strip()
    if not codec_ckpt or not denoiser_ckpt:
        raise RuntimeError(
            "Missing environment variables: BELEL_CODEC_CKPT and/or BELEL_DENOISER_CKPT"
        )

    device = os.environ.get("BELEL_DEVICE", "cuda").strip()
    dtype = os.environ.get("BELEL_DTYPE", "float16").strip()
    out_dir = os.environ.get("BELEL_OUT_DIR", "outputs/belel_edit_suite").strip()
    guidance = _safe_float(os.environ.get("BELEL_GUIDANCE", "6.0"), 6.0)

    seed_env = os.environ.get("BELEL_SEED", "").strip()
    seed = None if not seed_env else _safe_int(seed_env, 0)

    cfg = BelelHyperConfig(
        device=device,
        dtype=dtype,
        steps=2,
        guidance=float(guidance),
        seed=seed,
        out_dir=out_dir,
        codec_ckpt=codec_ckpt,
        denoiser_ckpt=denoiser_ckpt,
    )

    engine = BelelHyperEngine(cfg)
    engine.load_checkpoints()
    engine.to_device()
    return engine


app = FastAPI(title="BELEL Editing Suite", version="1.0.0")

# static UI
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/api/languages")
def api_languages():
    return {"count": len(BELEL_LANGUAGES), "languages": BELEL_LANGUAGES}


@app.post("/api/generate")
async def api_generate(
    prompt: str = Form(...),
    lyrics: str = Form(""),
    language: str = Form("en"),
    duration_sec: str = Form("60"),
    guidance: str = Form("6.0"),
    steps: str = Form("2"),
):
    """
    One-click generation using your BELEL engine.
    Writes wav + sidecars in job folder and returns paths.
    """
    _ensure_dir(JOBS_DIR)
    jid = _job_id()
    job_dir = JOBS_DIR / jid
    _ensure_dir(job_dir)

    engine = _resolve_engine_from_env()
    # force outputs into job_dir
    engine.cfg.out_dir = str(job_dir)

    lang = (language or "en").strip().lower()
    if lang not in {d["code"] for d in BELEL_LANGUAGES}:
        lang = "en"

    prompt_n = normalize_text_for_language(prompt, lang)
    lyrics_n = normalize_text_for_language(lyrics, lang)

    # BELEL-owned language conditioning: prefix a stable language tag (keeps everything local)
    prompt_cond = f"[lang={lang}] {prompt_n}".strip()

    req = BelelHyperRequest(
        prompt=prompt_cond,
        lyrics=lyrics_n,
        duration_sec=_safe_int(duration_sec, 60),
        filename="source.wav",
        steps=_safe_int(steps, 2),
        guidance=_safe_float(guidance, 6.0),
        extra={
            "ui": True,
            "suite": "belel_edit_suite",
            "mode": "generate",
            "language": lang,
            "prompt_raw_hash": _sha1(prompt),
            "lyrics_raw_hash": _sha1(lyrics),
        },
    )

    out = engine.run(req)

    resp = {
        "job_id": jid,
        "utc": _utc(),
        "wav_path": out["wav_path"],
        "mel_path": out["mel_path"],
        "wav_sidecar": out["wav_sidecar"],
        "meta": out.get("meta", {}),
    }
    _write_json(job_dir / "job.json", resp)
    return resp


@app.post("/api/edit")
async def api_edit(
    mode: str = Form(...),  # repaint|retake|extend|lyric_edit
    source_wav: UploadFile = File(...),
    # optional: sidecar json upload
    source_json: Optional[UploadFile] = File(None),

    # edits
    t_start_sec: str = Form("0"),
    t_end_sec: str = Form("0"),
    extend_sec: str = Form("0"),

    prompt: str = Form(""),
    lyrics: str = Form(""),
    new_lyrics: str = Form(""),

    language: str = Form("en"),
    steps: str = Form("2"),
    guidance: str = Form("6.0"),
    crossfade_ms: str = Form("60"),
    repaint_strength: str = Form("0.65"),
):
    """
    Unified edit endpoint:
      - repaint: regenerates region, preserves outside
      - retake: stronger repaint (more change)
      - extend: appends extra duration
      - lyric_edit: edits lyric region with new lyrics
    """
    _ensure_dir(JOBS_DIR)
    jid = _job_id()
    job_dir = JOBS_DIR / jid
    _ensure_dir(job_dir)

    # save uploads
    wav_path = job_dir / "input.wav"
    wav_bytes = await source_wav.read()
    wav_path.write_bytes(wav_bytes)

    json_path = job_dir / "input.json"
    if source_json is not None:
        json_bytes = await source_json.read()
        json_path.write_bytes(json_bytes)
    else:
        # optional fallback: if not provided, create empty
        json_path.write_text("{}", encoding="utf-8")

    engine = _resolve_engine_from_env()
    engine.cfg.out_dir = str(job_dir)

    # pipeline
    pipeline = BelelEditingPipeline(engine=engine)

    lang = (language or "en").strip().lower()
    if lang not in {d["code"] for d in BELEL_LANGUAGES}:
        lang = "en"

    # normalize and apply language tag
    prompt_n = normalize_text_for_language(prompt or "", lang)
    lyrics_n = normalize_text_for_language(lyrics or "", lang)
    new_lyrics_n = normalize_text_for_language(new_lyrics or "", lang)

    prompt_cond = f"[lang={lang}] {prompt_n}".strip() if prompt_n else f"[lang={lang}]"

    m = (mode or "").strip().lower()
    if m not in {"repaint", "retake", "extend", "lyric_edit"}:
        return JSONResponse(status_code=400, content={"error": f"invalid mode: {mode}"})

    edit_mode = {
        "repaint": BelelEditMode.REPAINT,
        "retake": BelelEditMode.RETAKE,
        "extend": BelelEditMode.EXTEND,
        "lyric_edit": BelelEditMode.LYRIC_EDIT,
    }[m]

    req = BelelEditRequest(
        mode=edit_mode,
        input_wav_path=str(wav_path),
        input_json_path=str(json_path),
        t_start_sec=float(_safe_float(t_start_sec, 0.0)),
        t_end_sec=float(_safe_float(t_end_sec, 0.0)),
        extend_sec=float(_safe_float(extend_sec, 0.0)),
        prompt=str(prompt_cond),
        lyrics=str(lyrics_n),
        new_lyrics=str(new_lyrics_n),
        steps=int(_safe_int(steps, 2)),
        guidance=float(_safe_float(guidance, 6.0)),
        crossfade_ms=int(_safe_int(crossfade_ms, 60)),
        repaint_strength=float(_safe_float(repaint_strength, 0.65)),
        extra={
            "ui": True,
            "suite": "belel_edit_suite",
            "language": lang,
            "mode": m,
            "prompt_raw_hash": _sha1(prompt or ""),
            "lyrics_raw_hash": _sha1(lyrics or ""),
            "new_lyrics_raw_hash": _sha1(new_lyrics or ""),
        },
    )

    out = pipeline.run(req, job_dir=str(job_dir))

    resp = {
        "job_id": jid,
        "utc": _utc(),
        "mode": m,
        "edited_wav": out["wav_path"],
        "edited_mel": out["mel_path"],
        "edited_json": out["wav_sidecar"],
        "meta": out.get("meta", {}),
        "details": out.get("details", {}),
    }
    _write_json(job_dir / "job.json", resp)
    return resp


@app.get("/api/job/{job_id}")
def api_job(job_id: str):
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return JSONResponse(status_code=404, content={"error": "job not found"})
    return _read_json(job_dir / "job.json")


@app.get("/api/download/{job_id}/wav")
def api_download_wav(job_id: str):
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return JSONResponse(status_code=404, content={"error": "job not found"})
    obj = _read_json(job_dir / "job.json")
    wav_path = Path(obj.get("edited_wav") or obj.get("wav_path") or "")
    if not wav_path.exists():
        return JSONResponse(status_code=404, content={"error": "wav not found"})
    return FileResponse(str(wav_path), media_type="audio/wav", filename=wav_path.name)


@app.get("/api/download/{job_id}/json")
def api_download_json(job_id: str):
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return JSONResponse(status_code=404, content={"error": "job not found"})
    obj = _read_json(job_dir / "job.json")
    json_path = Path(obj.get("edited_json") or obj.get("wav_sidecar") or "")
    if not json_path.exists():
        return JSONResponse(status_code=404, content={"error": "json not found"})
    return FileResponse(str(json_path), media_type="application/json", filename=json_path.name)


@app.get("/api/download/{job_id}/mel")
def api_download_mel(job_id: str):
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return JSONResponse(status_code=404, content={"error": "job not found"})
    obj = _read_json(job_dir / "job.json")
    mel_path = Path(obj.get("edited_mel") or obj.get("mel_path") or "")
    if not mel_path.exists():
        return JSONResponse(status_code=404, content={"error": "mel not found"})
    return FileResponse(str(mel_path), media_type="application/octet-stream", filename=mel_path.name)
