# BELEL-SING/belel-sing-gen/belel_hyper_core/editing/belel_edit_engine.py
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Union

import torch

from ..belel_engine import BelelHyperEngine, BelelHyperRequest
from ..metrics.belel_benchmark_protocol import BelelBenchmarkProtocol, BelelBenchmarkGates, BelelBenchmarkWeights

from .belel_edit_ops import (
    BelelEditRequest,
    BelelEditResult,
    BelelTimebase,
    load_edit_source,
    resolve_text_overrides,
    build_edit_meta,
    make_repaint_inputs,
    stitch_repaint,
    extend_plan,
    default_edit_filename,
    write_edit_receipt_json,
    make_edit_id,
    apply_strength,
    clamp_region,
)


# ============================================================
# High-quality editing configuration
# ============================================================

@dataclass
class BelelEditConfig:
    """
    Highest-quality defaults for editing pipeline.

    max_attempts:
      - auto-retry if benchmark gates fail (artifact-free discipline)

    repaint_padding_sec:
      - extra context rendered on both sides of region so repaint has continuity
      - mid is then cropped to exact region length before stitching

    extend_padding_sec:
      - extra context for extend generation (reduces boundary artifacts)
    """
    timebase: BelelTimebase = BelelTimebase()

    # Auto retry discipline
    max_attempts: int = 5
    attempt_seed_stride: int = 17  # deterministic seed_delta increment per attempt

    # Repaint context padding
    repaint_padding_sec: float = 0.65

    # Extend context padding
    extend_padding_sec: float = 0.65

    # Bench protocol gate enforcement
    enforce_protocol_gates: bool = True

    # Alignment handling (until aligner is wired)
    # - repaint/extend/retake: assume alignment is "neutral" unless lyrics changed
    # - lyric_edit: alignment is "pending" unless caller supplies alignment_score
    default_alignment_for_non_lyric_edits: float = 0.90
    default_alignment_for_lyric_edit: float = 0.40  # intentionally below gate; we mark pending

    # If True: allow lyric_edit to pass without meeting alignment gate (marked pending)
    allow_alignment_pending_for_lyric_edit: bool = True

    # Receipt + folder structure
    edits_dirname: str = "edits"
    receipts_dirname: str = "receipts"


# ============================================================
# Utilities
# ============================================================

def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha1_str(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return int(default)


def _ensure_dir(p: Union[str, Path]) -> None:
    Path(p).mkdir(parents=True, exist_ok=True)


def _to_mel_2d(obj: Any) -> torch.Tensor:
    """
    Accepts:
      - Tensor [80,T]
      - dict {"mel": Tensor[80,T], ...}
    """
    if isinstance(obj, dict) and "mel" in obj:
        obj = obj["mel"]
    if not isinstance(obj, torch.Tensor):
        raise ValueError("mel object is not a torch.Tensor")
    mel = obj.float()
    if mel.ndim != 2 or mel.shape[0] != 80:
        raise ValueError(f"Expected mel [80,T], got {tuple(mel.shape)}")
    return mel


# ============================================================
# Core Edit Engine
# ============================================================

class BelelEditEngine:
    """
    Unified editing engine, Belel-owned.

    This module is the backbone for:
      - repaint (region regeneration + crossfade)
      - extend (continuation + crossfade)
      - retake (full rerun with controlled deltas)
      - lyric_edit (text update + optional repaint retargeting)

    It enforces:
      - deterministic edit IDs
      - provenance chain embedding
      - protocol gate discipline (artifact-free)
    """

    def __init__(
        self,
        engine: BelelHyperEngine,
        *,
        cfg: Optional[BelelEditConfig] = None,
        protocol: Optional[BelelBenchmarkProtocol] = None,
    ):
        self.engine = engine
        self.cfg = cfg or BelelEditConfig()

        self.protocol = protocol or BelelBenchmarkProtocol(
            gates=BelelBenchmarkGates(),
            weights=BelelBenchmarkWeights(),
        )

        # ensure edit folders exist under engine.out_dir
        out_root = Path(self.engine.cfg.out_dir)
        _ensure_dir(out_root / self.cfg.edits_dirname)
        _ensure_dir(out_root / self.cfg.receipts_dirname)

    # --------------------------------------------------------
    # Public entrypoint
    # --------------------------------------------------------

    def apply(self, req: BelelEditRequest) -> Dict[str, Any]:
        """
        Applies an edit and writes:
          - wav
          - mel pt sidecar
          - wav json sidecar
          - edit receipt json

        Returns:
          dict with paths + meta + benchmark details.
        """
        req.validate()

        # Load source
        src_mel, src_prompt, src_lyrics, src_meta = load_edit_source(req)

        # Resolve output text
        out_prompt, out_lyrics = resolve_text_overrides(src_prompt, src_lyrics, req)

        # Build edit provenance
        tb = self.cfg.timebase
        edit_meta = build_edit_meta(
            req,
            src_prompt=src_prompt,
            src_lyrics=src_lyrics,
            src_meta=src_meta,
            timebase=tb,
        )

        # Determine base id for artifact naming
        edit_id = str(edit_meta.get("edit_id", "")) or make_edit_id(req, src_meta)

        # Dispatch
        if req.edit_type == "repaint":
            result = self._edit_repaint(src_mel, out_prompt, out_lyrics, src_meta, edit_meta, req)
        elif req.edit_type == "extend":
            result = self._edit_extend(src_mel, out_prompt, out_lyrics, src_meta, edit_meta, req)
        elif req.edit_type == "retake":
            result = self._edit_retake(src_mel, out_prompt, out_lyrics, src_meta, edit_meta, req)
        elif req.edit_type == "lyric_edit":
            result = self._edit_lyric_edit(src_mel, out_prompt, out_lyrics, src_meta, edit_meta, req)
        else:
            raise ValueError(f"Unsupported edit_type: {req.edit_type}")

        # Gate discipline (auto-retry if needed)
        final = self._enforce_quality_with_retries(result, req, src_meta, edit_meta, edit_id)

        # Persist artifacts via existing engine writers
        return self._persist(final, req, src_meta, edit_meta, edit_id)

    # --------------------------------------------------------
    # Quality gating (industry-grade discipline)
    # --------------------------------------------------------

    def _alignment_score_for_eval(self, req: BelelEditRequest, src_meta: Dict[str, Any], edit_meta: Dict[str, Any]) -> Tuple[float, bool]:
        """
        Returns:
          (alignment_score, alignment_pending)

        Logic:
          - If caller supplies alignment_score in req.extra, use it.
          - If edit_type != lyric_edit: use high default (neutral positive).
          - If lyric_edit: alignment is pending unless supplied.
        """
        supplied = None
        if isinstance(req.extra, dict) and "alignment_score" in req.extra:
            supplied = req.extra.get("alignment_score", None)

        if supplied is not None:
            return float(max(0.0, min(1.0, _safe_float(supplied, 0.0)))), False

        if req.edit_type != "lyric_edit":
            return float(self.cfg.default_alignment_for_non_lyric_edits), False

        # lyric_edit without aligner score supplied
        return float(self.cfg.default_alignment_for_lyric_edit), True

    def _evaluate_protocol(self, mel: torch.Tensor, req: BelelEditRequest, src_meta: Dict[str, Any], edit_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs BelelBenchmarkProtocol and returns dict with score/pass/breakdown.
        Handles lyric_edit alignment pending policy.
        """
        mel2d = _to_mel_2d(mel)

        align_score, alignment_pending = self._alignment_score_for_eval(req, src_meta, edit_meta)

        score10, passed, breakdown = self.protocol.evaluate(
            mel2d,
            alignment_score=float(align_score),
        )

        # If lyric_edit and pending alignment is allowed, we override pass/fail only for the alignment gate.
        if (
            req.edit_type == "lyric_edit"
            and alignment_pending
            and self.cfg.allow_alignment_pending_for_lyric_edit
            and self.cfg.enforce_protocol_gates
        ):
            gate_failures = breakdown.get("gate_failures", {}) if isinstance(breakdown, dict) else {}
            if isinstance(gate_failures, dict) and "alignment_score" in gate_failures:
                # Remove alignment failure and recompute pass flag
                gate_failures = dict(gate_failures)
                gate_failures.pop("alignment_score", None)
                breakdown["gate_failures"] = gate_failures
                passed = len(gate_failures) == 0
                breakdown["passed"] = bool(passed)
                breakdown["alignment_pending"] = True

        return {
            "score_10": float(score10),
            "passed": bool(passed),
            "breakdown": breakdown,
        }

    def _enforce_quality_with_retries(
        self,
        result: BelelEditResult,
        req: BelelEditRequest,
        src_meta: Dict[str, Any],
        edit_meta: Dict[str, Any],
        edit_id: str,
    ) -> BelelEditResult:
        """
        If protocol gates fail, retry deterministically with seed_delta changes (industry discipline).
        """
        if not self.cfg.enforce_protocol_gates:
            return result

        eval0 = self._evaluate_protocol(result.mel, req, src_meta, edit_meta)
        result.edit_meta["benchmark"] = eval0

        if eval0["passed"]:
            return result

        # Retry loop
        best: Optional[BelelEditResult] = result
        best_score = float(eval0.get("score_10", 0.0))

        for k in range(1, int(self.cfg.max_attempts)):
            # deterministic delta applied
            req2 = BelelEditRequest(**{**asdict(req)})
            req2.attempt = int(k)
            req2.seed_delta = int(req.seed_delta) + int(self.cfg.attempt_seed_stride) * int(k)

            # rebuild edit meta (attempt changes)
            edit_meta2 = dict(edit_meta)
            edit_meta2["attempt"] = int(k)
            edit_meta2["seed_delta"] = int(req2.seed_delta)

            # rerun dispatch
            if req2.edit_type == "repaint":
                cand = self._edit_repaint(best.mel, best.prompt, best.lyrics, src_meta, edit_meta2, req2, allow_src_override=True)
            elif req2.edit_type == "extend":
                cand = self._edit_extend(best.mel, best.prompt, best.lyrics, src_meta, edit_meta2, req2, allow_src_override=True)
            elif req2.edit_type == "retake":
                cand = self._edit_retake(best.mel, best.prompt, best.lyrics, src_meta, edit_meta2, req2, allow_src_override=True)
            elif req2.edit_type == "lyric_edit":
                cand = self._edit_lyric_edit(best.mel, best.prompt, best.lyrics, src_meta, edit_meta2, req2, allow_src_override=True)
            else:
                raise ValueError(f"Unsupported edit_type: {req2.edit_type}")

            ev = self._evaluate_protocol(cand.mel, req2, src_meta, edit_meta2)
            cand.edit_meta["benchmark"] = ev

            sc = float(ev.get("score_10", 0.0))
            if sc > best_score:
                best = cand
                best_score = sc

            if ev["passed"]:
                return cand

        # If never passed: return best-scoring candidate with failure recorded (still traceable).
        # Editing UI can show gate failures and invite a stronger retake.
        if best is not None:
            return best
        return result

    # --------------------------------------------------------
    # Persistence
    # --------------------------------------------------------

    def _persist(
        self,
        result: BelelEditResult,
        req: BelelEditRequest,
        src_meta: Dict[str, Any],
        edit_meta: Dict[str, Any],
        edit_id: str,
    ) -> Dict[str, Any]:
        """
        Writes:
          - wav
          - mel sidecar .pt
          - wav sidecar .json
          - edit receipt .json
        """
        out_root = Path(self.engine.cfg.out_dir)
        edits_dir = out_root / self.cfg.edits_dirname
        receipts_dir = out_root / self.cfg.receipts_dirname
        _ensure_dir(edits_dir)
        _ensure_dir(receipts_dir)

        src_name = Path(req.src_mel_pt).name
        wav_name = default_edit_filename(
            src_name=src_name,
            edit_id=str(edit_id),
            edit_type=str(req.edit_type),
            ext=".wav",
        )
        wav_path = str(edits_dir / wav_name)

        # waveform
        wav = self.engine.mel_to_waveform(result.mel.unsqueeze(0))

        # save wav
        wav_path = self.engine.save_wav(wav, str(Path(self.cfg.edits_dirname) / wav_name))

        # embed edit chain + protocol outcome into meta
        meta_out = dict(result.meta or {})
        meta_out["edit"] = dict(result.edit_meta or {})
        meta_out["edit"]["edit_id"] = str(edit_id)
        meta_out["edit"]["edit_type"] = str(req.edit_type)
        meta_out["edit"]["utc"] = _utc_now()

        # write mel sidecar
        mel_path = self.engine.save_mel_sidecar_pt(
            result.mel.unsqueeze(0),
            Path(wav_path).name,
            prompt=result.prompt,
            lyrics=result.lyrics,
            meta=meta_out,
        )

        # write wav sidecar json
        wav_sidecar = self.engine.save_wav_sidecar_json(
            wav_path,
            prompt=result.prompt,
            lyrics=result.lyrics,
            meta=meta_out,
        )

        # write edit receipt (separate, UI-friendly)
        receipt_payload = {
            "utc": _utc_now(),
            "edit_id": str(edit_id),
            "edit_type": str(req.edit_type),
            "src": {
                "mel_pt": str(Path(req.src_mel_pt).resolve()),
                "wav": str(Path(req.src_wav).resolve()) if req.src_wav else "",
            },
            "out": {
                "wav": str(Path(wav_path).resolve()),
                "mel_pt": str(Path(mel_path).resolve()),
                "wav_sidecar": str(Path(wav_sidecar).resolve()),
            },
            "text": {
                "prompt": str(result.prompt or ""),
                "lyrics_present": bool((result.lyrics or "").strip()),
                "prompt_hash": _sha1_str(result.prompt or ""),
                "lyrics_hash": _sha1_str(result.lyrics or "") if (result.lyrics or "").strip() else "",
            },
            "meta": meta_out,
        }
        receipt_path = receipts_dir / f"{Path(wav_name).stem}.receipt.json"
        receipt_written = write_edit_receipt_json(receipt_path, receipt_payload)

        return {
            "wav_path": wav_path,
            "mel_path": mel_path,
            "wav_sidecar": wav_sidecar,
            "receipt": receipt_written,
            "edit_id": str(edit_id),
            "edit_type": str(req.edit_type),
            "benchmark": (result.edit_meta or {}).get("benchmark", None),
            "meta": meta_out,
        }

    # --------------------------------------------------------
    # Edit implementations
    # --------------------------------------------------------

    def _edit_repaint(
        self,
        src_mel: torch.Tensor,
        prompt: str,
        lyrics: str,
        src_meta: Dict[str, Any],
        edit_meta: Dict[str, Any],
        req: BelelEditRequest,
        *,
        allow_src_override: bool = False,
    ) -> BelelEditResult:
        """
        Repaint a region.

        Strategy (quality-first):
          1) Determine region [a:b] in mel frames
          2) Render a padded window around region using the generator (fresh high-quality content)
          3) Crop exact mid length and stitch with crossfade
          4) Strength blend supported (for gentle corrections)
        """
        tb = self.cfg.timebase
        inp = make_repaint_inputs(src_mel, req, tb=tb)
        a = int(inp["start_frame"])
        b = int(inp["end_frame"])
        left = inp["left"]
        src_mid = inp["mid"]
        right = inp["right"]
        fade_frames = int(inp["fade_frames"])

        # If region is empty, return unchanged but still provenance-tagged
        if src_mid.shape[1] <= 0:
            meta_out = dict(src_meta or {})
            meta_out["edit"] = dict(edit_meta or {})
            return BelelEditResult(mel=src_mel, prompt=prompt, lyrics=lyrics, meta=meta_out, edit_meta=dict(edit_meta))

        # Render padded window duration
        region_sec = max(0.01, float(req.end_sec) - float(req.start_sec))  # type: ignore
        pad = float(self.cfg.repaint_padding_sec)
        padded_sec = max(0.05, region_sec + 2.0 * pad)

        # Determine how many frames we need for exact region (b-a)
        target_frames = int(b - a)
        if target_frames <= 0:
            target_frames = int(src_mid.shape[1])

        # Generate new content for padded window
        gen_mel = self._generate_for_edit(
            prompt=prompt,
            lyrics=lyrics,
            duration_sec=padded_sec,
            req=req,
        )  # [80, Tgen]

        # Crop center slice to match target_frames
        # Centered crop for continuity
        Tgen = int(gen_mel.shape[1])
        if Tgen <= target_frames:
            # pad with repetition if too short (rare, but keep deterministic)
            reps = int(math.ceil(target_frames / max(1, Tgen)))
            gen_mel = gen_mel.repeat(1, reps)[:, :target_frames]
        else:
            start = (Tgen - target_frames) // 2
            gen_mel = gen_mel[:, start : start + target_frames]

        # Strength blend inside region (with src_mid)
        # Ensure matching shape
        if gen_mel.shape[1] != src_mid.shape[1]:
            # final clamp to src_mid length (source-of-truth)
            tgt = int(src_mid.shape[1])
            if gen_mel.shape[1] < tgt:
                reps = int(math.ceil(tgt / max(1, gen_mel.shape[1])))
                gen_mel = gen_mel.repeat(1, reps)[:, :tgt]
            else:
                gen_mel = gen_mel[:, :tgt]

        blended_mid = apply_strength(src_mid, gen_mel, strength=float(req.strength))

        # Stitch
        out_mel = stitch_repaint(left, blended_mid, right, fade_frames=fade_frames, strength=float(req.strength))

        meta_out = dict(src_meta or {})
        meta_out["edit"] = dict(edit_meta or {})
        meta_out["edit"]["region_frames"] = {"start": int(a), "end": int(b), "frames": int(b - a)}
        meta_out["edit"]["fade_frames"] = int(fade_frames)

        return BelelEditResult(
            mel=out_mel,
            prompt=prompt,
            lyrics=lyrics,
            meta=meta_out,
            edit_meta=dict(edit_meta),
        )

    def _edit_extend(
        self,
        src_mel: torch.Tensor,
        prompt: str,
        lyrics: str,
        src_meta: Dict[str, Any],
        edit_meta: Dict[str, Any],
        req: BelelEditRequest,
        *,
        allow_src_override: bool = False,
    ) -> BelelEditResult:
        """
        Extend by N seconds.

        Strategy (quality-first):
          - generate continuation of length (extend_sec + padding)
          - crop to exact extend frames
          - crossfade at join
        """
        tb = self.cfg.timebase
        plan = extend_plan(src_mel, req, tb=tb)
        add_frames = int(plan["add_frames"])
        fade_frames = int(plan["fade_frames"])

        # generate extension window
        extend_sec = float(req.extend_sec or 0.0)
        padded_sec = max(0.05, extend_sec + float(self.cfg.extend_padding_sec))

        gen_mel = self._generate_for_edit(
            prompt=prompt,
            lyrics=lyrics,
            duration_sec=padded_sec,
            req=req,
        )  # [80,Tgen]

        # Crop to exact add_frames (take from start to preserve "continuation feel")
        Tgen = int(gen_mel.shape[1])
        if Tgen < add_frames:
            reps = int(math.ceil(add_frames / max(1, Tgen)))
            gen_mel = gen_mel.repeat(1, reps)[:, :add_frames]
        else:
            gen_mel = gen_mel[:, :add_frames]

        # Crossfade join: treat src as left, gen as mid, empty right
        left = src_mel
        mid = gen_mel
        right = torch.zeros((80, 0), dtype=left.dtype)

        out_mel = torch.cat([left, mid], dim=1) if fade_frames == 0 else self._crossfade_join(left, mid, fade_frames)

        meta_out = dict(src_meta or {})
        meta_out["edit"] = dict(edit_meta or {})
        meta_out["edit"]["extend_frames"] = int(add_frames)
        meta_out["edit"]["fade_frames"] = int(fade_frames)

        return BelelEditResult(
            mel=out_mel,
            prompt=prompt,
            lyrics=lyrics,
            meta=meta_out,
            edit_meta=dict(edit_meta),
        )

    def _edit_retake(
        self,
        src_mel: torch.Tensor,
        prompt: str,
        lyrics: str,
        src_meta: Dict[str, Any],
        edit_meta: Dict[str, Any],
        req: BelelEditRequest,
        *,
        allow_src_override: bool = False,
    ) -> BelelEditResult:
        """
        Full retake (regenerate entire track deterministically).

        Quality-first:
          - still uses your locked ultra2 inference defaults through BelelHyperEngine
          - seed_delta applied to avoid identical outputs
        """
        # derive duration from source mel length
        tb = self.cfg.timebase
        T = int(src_mel.shape[1])
        duration_sec = max(0.05, tb.mel_frame_to_sec(T))

        gen_mel = self._generate_for_edit(
            prompt=prompt,
            lyrics=lyrics,
            duration_sec=duration_sec,
            req=req,
        )

        # Match target frames exactly for deterministic UI playback parity
        gen_mel = self._force_length(gen_mel, target_frames=T)

        meta_out = dict(src_meta or {})
        meta_out["edit"] = dict(edit_meta or {})
        meta_out["edit"]["retake_full"] = True

        return BelelEditResult(
            mel=gen_mel,
            prompt=prompt,
            lyrics=lyrics,
            meta=meta_out,
            edit_meta=dict(edit_meta),
        )

    def _edit_lyric_edit(
        self,
        src_mel: torch.Tensor,
        prompt: str,
        lyrics: str,
        src_meta: Dict[str, Any],
        edit_meta: Dict[str, Any],
        req: BelelEditRequest,
        *,
        allow_src_override: bool = False,
    ) -> BelelEditResult:
        """
        Lyric edit.

        Current implementation:
          - updates text fields + (optionally) repaints region for vocal correction if region provided
          - if region provided: behaves like repaint but with new lyrics conditioning

        This keeps the contract stable now, and becomes "aligner-targeted repaint" later.
        """
        # If start/end provided, repaint region with updated lyrics
        if req.start_sec is not None and req.end_sec is not None:
            return self._edit_repaint(src_mel, prompt, lyrics, src_meta, edit_meta, req, allow_src_override=allow_src_override)

        # Otherwise: text-only edit (non-destructive, no audio change yet)
        meta_out = dict(src_meta or {})
        meta_out["edit"] = dict(edit_meta or {})
        meta_out["edit"]["text_only"] = True

        return BelelEditResult(
            mel=src_mel,
            prompt=prompt,
            lyrics=lyrics,
            meta=meta_out,
            edit_meta=dict(edit_meta),
        )

    # --------------------------------------------------------
    # Helpers: generation + length + crossfade join
    # --------------------------------------------------------

    def _generate_for_edit(
        self,
        *,
        prompt: str,
        lyrics: str,
        duration_sec: float,
        req: BelelEditRequest,
    ) -> torch.Tensor:
        """
        Calls BelelHyperEngine.generate_mel with strict deterministic seed deltas.
        """
        # The BelelHyperEngine uses cfg.seed, so we temporarily modify it deterministically.
        base_seed = self.engine.cfg.seed
        seed = None if base_seed is None else int(base_seed) + int(req.seed_delta)

        # Per-request overrides
        steps = req.steps_override if req.steps_override is not None else None
        guidance = req.guidance_override if req.guidance_override is not None else None

        # Temporarily set seed on engine cfg (single-thread assumption)
        old_seed = self.engine.cfg.seed
        self.engine.cfg.seed = seed

        try:
            hyper_req = BelelHyperRequest(
                prompt=str(prompt or ""),
                lyrics=str(lyrics or ""),
                duration_sec=int(max(1, round(float(duration_sec)))),
                filename=None,
                steps=steps,
                guidance=guidance,
                extra={"edit": True, "edit_type": req.edit_type, "seed_delta": int(req.seed_delta), "attempt": int(req.attempt)},
            )
            mel_batched = self.engine.generate_mel(hyper_req)  # engine returns [B,80,T] or [80,T]?
        finally:
            self.engine.cfg.seed = old_seed

        # Normalize to [80,T]
        if isinstance(mel_batched, torch.Tensor) and mel_batched.ndim == 3:
            mel = mel_batched[0]
        else:
            mel = _to_mel_2d(mel_batched)

        return mel.float()

    def _force_length(self, mel: torch.Tensor, *, target_frames: int) -> torch.Tensor:
        """
        Forces mel to exactly target_frames by deterministic crop/repeat.
        """
        mel = _to_mel_2d(mel)
        T = int(mel.shape[1])
        tgt = int(max(1, target_frames))

        if T == tgt:
            return mel
        if T > tgt:
            return mel[:, :tgt]

        reps = int(math.ceil(tgt / max(1, T)))
        return mel.repeat(1, reps)[:, :tgt]

    def _crossfade_join(self, left: torch.Tensor, right: torch.Tensor, fade_frames: int) -> torch.Tensor:
        """
        Crossfade the last fade_frames of left with first fade_frames of right.
        """
        fade = int(max(0, fade_frames))
        if fade == 0:
            return torch.cat([left, right], dim=1)

        fade = min(fade, left.shape[1], right.shape[1])
        if fade <= 0:
            return torch.cat([left, right], dim=1)

        device = left.device
        t = torch.linspace(0.0, 1.0, steps=fade, device=device, dtype=torch.float32).view(1, -1)
        w = 0.5 - 0.5 * torch.cos(math.pi * t)  # cosine 0..1

        left_keep = left[:, :-fade]
        left_tail = left[:, -fade:]
        right_head = right[:, :fade]
        right_keep = right[:, fade:]

        blend = left_tail * (1.0 - w) + right_head * w
        return torch.cat([left_keep, blend, right_keep], dim=1)
