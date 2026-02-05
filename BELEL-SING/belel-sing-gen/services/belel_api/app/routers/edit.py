from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from ..schemas.edit import EditRequest, EditResponse, BenchmarkBlock
from ..settings import settings
from ..core.edit_singleton import get_editor
from ..core.paths import resolve_sandbox_root
from ..storage.project_index import ProjectIndex

router = APIRouter(tags=["edit"])


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/api/edit", response_model=EditResponse)
def edit(req: EditRequest):
    """
    Calls BelelEditEngine.apply() and persists the returned artifact paths + receipt.

    Assumptions:
      - editor.apply accepts dict (req.model_dump()) and returns dict in your persisted format.
      - edit_id is deterministic (content+params hash) on your side.
    """
    editor = get_editor()
    root = resolve_sandbox_root(settings.out_dir)
    idx = ProjectIndex((root / settings.project_index_relpath).resolve())

    try:
        out = editor.apply(req.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"editor.apply failed: {e}")

    # Required fields
    project_id = out.get("project_id")
    version_id = out.get("version_id")
    wav_path = out.get("wav_path")
    mel_path = out.get("mel_path")
    wav_sidecar = out.get("wav_sidecar") or out.get("wav_sidecar_path")
    receipt = out.get("receipt")
    edit_id = out.get("edit_id")
    edit_type = out.get("edit_type") or req.edit_type
    meta = out.get("meta") or {}

    missing = [k for k, v in [("project_id", project_id), ("version_id", version_id), ("wav_path", wav_path),
                             ("mel_path", mel_path), ("wav_sidecar", wav_sidecar), ("receipt", receipt),
                             ("edit_id", edit_id)] if not v]
    if missing:
        raise HTTPException(status_code=500, detail=f"editor.apply missing fields: {missing}")

    # Benchmark normalize
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

    # Persist into project index for library/history
    utc = _utc()
    title = (meta.get("title") or "Untitled") if isinstance(meta, dict) else "Untitled"
    idx.upsert_project(project_id=project_id, title=title, utc=utc)

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
            "receipt": receipt,
            "edit_id": edit_id,
            "edit_type": edit_type,
            "benchmark": bench_block.model_dump() if bench_block else None,
            "meta": meta,
            "committed": False
        },
        set_active=True,
    )

    return EditResponse(
        project_id=project_id,
        version_id=version_id,
        wav_path=wav_path,
        mel_path=mel_path,
        wav_sidecar=wav_sidecar,
        receipt=receipt,
        edit_id=edit_id,
        edit_type=edit_type,
        benchmark=bench_block,
        meta=meta if isinstance(meta, dict) else {"meta": meta},
    )
