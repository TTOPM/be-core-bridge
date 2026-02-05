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
    root = resolve_sandbox_root(settings.out_dir)
    idx = ProjectIndex((root / settings.project_index_relpath).resolve())

    project_id = None
    # allow engine to assign project id, but ensure we always have one
    try:
        # engine.generate returns dict with wav_path/mel_path/wav_sidecar/meta
        out = engine.generate(
            prompt=req.prompt,
            lyrics=req.lyrics,
            duration_sec=req.duration_sec,
            language=req.language,
            steps=req.steps,
            guidance=req.guidance,
            seed=req.seed,
            codec_ckpt=req.codec_ckpt,
            denoiser_ckpt=req.denoiser_ckpt,
            meta=req.meta or {"client": "belel-studio", "ui_version": "0.1.0"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"engine.generate failed: {e}")

    # normalize expected fields
    wav_path = out.get("wav_path")
    mel_path = out.get("mel_path")
    wav_sidecar = out.get("wav_sidecar") or out.get("wav_sidecar_path")
    meta = out.get("meta") or req.meta or {}

    if not wav_path or not mel_path or not wav_sidecar:
        raise HTTPException(status_code=500, detail="engine.generate did not return wav_path/mel_path/wav_sidecar")

    project_id = out.get("project_id") or meta.get("project_id") or f"prj_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    version_id = out.get("version_id") or "v0"

    title = (meta.get("title") or "Untitled") if isinstance(meta, dict) else "Untitled"
    utc = _utc()

    idx.upsert_project(project_id=project_id, title=title, utc=utc)

    # benchmark is optional here; your engine may already compute it
    benchmark = out.get("benchmark")
    bench_block = None
    if isinstance(benchmark, dict) and "score_10" in benchmark and "passed" in benchmark:
        bench_block = BenchmarkBlock(
            score_10=float(benchmark["score_10"]),
            passed=bool(benchmark["passed"]),
            breakdown=benchmark.get("breakdown"),
            alignment_pending=benchmark.get("alignment_pending"),
            gate_failures=benchmark.get("gate_failures"),
        )

    idx.append_version(
        project_id=project_id,
        version={
            "project_id": project_id,
            "version_id": version_id,
            "utc": utc,
            "title": title,
            "wav_path": wav_path,
            "mel_path": mel_path,
            "wav_sidecar": wav_sidecar,
            "receipt": out.get("receipt"),
            "edit_id": out.get("edit_id"),
            "edit_type": out.get("edit_type") or "generate",
            "benchmark": bench_block.model_dump() if bench_block else None,
            "meta": meta,
            "committed": False
        },
        set_active=True,
    )

    return GenerateResponse(
        project_id=project_id,
        version_id=version_id,
        wav_path=wav_path,
        mel_path=mel_path,
        wav_sidecar=wav_sidecar,
        meta=meta if isinstance(meta, dict) else {"meta": meta},
        benchmark=bench_block,
    )
