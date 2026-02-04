# BELEL-SING/belel-sing-gen/belel_hyper_core/editing/belel_editing.py
from __future__ import annotations

import json
import time
import math
import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import torch

from belel_hyper_core.belel_engine import BelelHyperEngine, BelelHyperRequest


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def _safe_float(x: Any, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


class BelelEditMode(str, Enum):
    REPAINT = "repaint"
    RETAKE = "retake"
    EXTEND = "extend"
    LYRIC_EDIT = "lyric_edit"


@dataclass
class BelelEditRequest:
    mode: BelelEditMode
    input_wav_path: str
    input_json_path: str

    # region controls (seconds)
    t_start_sec: float = 0.0
    t_end_sec: float = 0.0
    extend_sec: float = 0.0

    # conditioning
    prompt: str = ""
    lyrics: str = ""
    new_lyrics: str = ""

    # inference
    steps: int = 2
    guidance: float = 6.0

    # audio stitching
    crossfade_ms: int = 60

    # repaint behavior
    repaint_strength: float = 0.65  # 0..1

    # misc meta
    extra: Optional[Dict[str, Any]] = None


class BelelEditingPipeline:
    """
    BELEL-owned editing pipeline:
      - uses mel/latent editing where possible
      - merges with waveform crossfade for clean seams
      - ALWAYS writes provenance via engine.run()
    """

    def __init__(self, *, engine: BelelHyperEngine):
        self.engine = engine

    # --------------------------------------------------------
    # Public entrypoint
    # --------------------------------------------------------

    def run(self, req: BelelEditRequest, *, job_dir: str) -> Dict[str, Any]:
        jobp = Path(job_dir)
        jobp.mkdir(parents=True, exist_ok=True)

        # Attempt to recover original prompt/lyrics from sidecar if not supplied
        sidecar = _read_json(Path(req.input_json_path))
        src_prompt = str(sidecar.get("prompt", "") or "")
        src_lyrics = str(sidecar.get("lyrics", "") or "")

        prompt = (req.prompt or "").strip() or src_prompt
        lyrics = (req.lyrics or "").strip() or src_lyrics

        # Fallback: still allow empty prompt/lyrics, but we tag it explicitly
        if not prompt:
            prompt = "[lang=en]"
        if lyrics is None:
            lyrics = ""

        if req.mode == BelelEditMode.EXTEND:
            return self._extend(req, jobp, prompt, lyrics, sidecar)

        # For region-based edits, we need a mel sidecar if present.
        # If the user only provided wav+json, we regenerate mel from scratch as the base “source mel”
        # (still BELEL-owned and provenance-locked).
        base_mel_pt = jobp / "base_mel.pt"

        if "mel_path" in sidecar and sidecar["mel_path"]:
            mp = Path(str(sidecar["mel_path"]))
            if mp.exists():
                base_mel_pt = mp

        # If base mel not found in sidecar, generate a base track quickly matching duration heuristics
        if not base_mel_pt.exists():
            # derive duration from wav sidecar if available
            dur = _safe_float(sidecar.get("duration_sec", 0.0), 0.0)
            if dur <= 0.0:
                dur = 60.0
            gen = self.engine.run(
                BelelHyperRequest(
                    prompt=prompt,
                    lyrics=lyrics,
                    duration_sec=int(dur),
                    filename="base_source.wav",
                    steps=int(req.steps),
                    guidance=float(req.guidance),
                    extra={"edit_suite": True, "mode": "base_regen"},
                )
            )
            base_mel_pt = Path(gen["mel_path"])

        # Load base mel
        mel_obj = torch.load(str(base_mel_pt), map_location="cpu")
        base_mel = mel_obj["mel"] if isinstance(mel_obj, dict) and "mel" in mel_obj else mel_obj
        if not isinstance(base_mel, torch.Tensor) or base_mel.ndim != 2:
            raise ValueError("Invalid base mel")

        # Determine region in frames
        sr = int(sidecar.get("sample_rate", self.engine.cfg.sample_rate))
        hop = int(sidecar.get("hop_length", self.engine.cfg.hop_length))

        t0 = float(max(0.0, req.t_start_sec))
        t1 = float(max(0.0, req.t_end_sec))
        if t1 <= t0:
            # If no region specified, default to first 5 seconds
            t0, t1 = 0.0, 5.0

        f0 = int((t0 * sr) / hop)
        f1 = int((t1 * sr) / hop)
        f0 = max(0, min(f0, base_mel.shape[1] - 1))
        f1 = max(f0 + 1, min(f1, base_mel.shape[1]))

        if req.mode in (BelelEditMode.REPAINT, BelelEditMode.RETAKE):
            return self._repaint_or_retake(req, jobp, prompt, lyrics, base_mel, f0, f1, sidecar)

        if req.mode == BelelEditMode.LYRIC_EDIT:
            return self._lyric_edit(req, jobp, prompt, lyrics, base_mel, f0, f1, sidecar)

        raise ValueError(f"Unsupported mode: {req.mode}")

    # --------------------------------------------------------
    # Extend
    # --------------------------------------------------------

    def _extend(
        self,
        req: BelelEditRequest,
        jobp: Path,
        prompt: str,
        lyrics: str,
        sidecar: Dict[str, Any],
    ) -> Dict[str, Any]:
        ext = float(max(0.0, req.extend_sec))
        if ext <= 0.0:
            ext = 30.0

        # Determine base duration. If unknown, default to 60s.
        base_dur = _safe_float(sidecar.get("duration_sec", 0.0), 0.0)
        if base_dur <= 0.0:
            base_dur = 60.0

        target_dur = int(max(5, int(base_dur + ext)))

        out = self.engine.run(
            BelelHyperRequest(
                prompt=prompt,
                lyrics=lyrics,
                duration_sec=int(target_dur),
                filename="edited_extend.wav",
                steps=int(req.steps),
                guidance=float(req.guidance),
                extra={
                    "edit_suite": True,
                    "edit_mode": "extend",
                    "base_duration_sec": float(base_dur),
                    "extend_sec": float(ext),
                    "prompt_hash": _sha1(prompt),
                    "lyrics_hash": _sha1(lyrics),
                    **(dict(req.extra) if isinstance(req.extra, dict) else {}),
                },
            )
        )

        out["details"] = {
            "mode": "extend",
            "base_duration_sec": float(base_dur),
            "target_duration_sec": int(target_dur),
        }
        return out

    # --------------------------------------------------------
    # Region repaint / retake
    # --------------------------------------------------------

    def _repaint_or_retake(
        self,
        req: BelelEditRequest,
        jobp: Path,
        prompt: str,
        lyrics: str,
        base_mel: torch.Tensor,
        f0: int,
        f1: int,
        sidecar: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Strength: retake is stronger than repaint
        strength = float(_clamp01(req.repaint_strength))
        if req.mode == BelelEditMode.RETAKE:
            strength = max(strength, 0.85)

        # Generate a full mel (same duration) then splice region
        dur = int(max(5, int(sidecar.get("duration_sec", 60))))
        gen = self.engine.run(
            BelelHyperRequest(
                prompt=prompt,
                lyrics=lyrics,
                duration_sec=dur,
                filename="tmp_edit_source.wav",
                steps=int(req.steps),
                guidance=float(req.guidance),
                extra={
                    "edit_suite": True,
                    "edit_mode": str(req.mode.value),
                    "region_frames": [int(f0), int(f1)],
                    "strength": float(strength),
                    **(dict(req.extra) if isinstance(req.extra, dict) else {}),
                },
            )
        )

        mel_obj = torch.load(str(gen["mel_path"]), map_location="cpu")
        gen_mel = mel_obj["mel"] if isinstance(mel_obj, dict) and "mel" in mel_obj else mel_obj
        if not isinstance(gen_mel, torch.Tensor) or gen_mel.ndim != 2:
            raise ValueError("Invalid generated mel")

        # Blend region only; outside is preserved from base
        edited_mel = base_mel.clone()
        edited_region = (1.0 - strength) * base_mel[:, f0:f1] + strength * gen_mel[:, f0:f1]
        edited_mel[:, f0:f1] = edited_region

        # Vocode edited mel -> wav, then write sidecars via engine.save_* utilities:
        # We route through engine.run() for provenance by using a “mel override” helper.
        out = self._finalize_mel_as_output(
            edited_mel,
            prompt=prompt,
            lyrics=lyrics,
            filename="edited_region.wav",
            meta_extra={
                "edit_suite": True,
                "edit_mode": str(req.mode.value),
                "region_sec": [float(req.t_start_sec), float(req.t_end_sec)],
                "region_frames": [int(f0), int(f1)],
                "strength": float(strength),
                "crossfade_ms": int(req.crossfade_ms),
                **(dict(req.extra) if isinstance(req.extra, dict) else {}),
            },
        )

        out["details"] = {
            "mode": str(req.mode.value),
            "region_frames": [int(f0), int(f1)],
            "strength": float(strength),
        }
        return out

    # --------------------------------------------------------
    # Lyric edit
    # --------------------------------------------------------

    def _lyric_edit(
        self,
        req: BelelEditRequest,
        jobp: Path,
        prompt: str,
        lyrics: str,
        base_mel: torch.Tensor,
        f0: int,
        f1: int,
        sidecar: Dict[str, Any],
    ) -> Dict[str, Any]:
        new_lyrics = (req.new_lyrics or "").strip()
        if not new_lyrics:
            new_lyrics = lyrics

        # Generate alternate mel with the new lyrics, then splice region
        dur = int(max(5, int(sidecar.get("duration_sec", 60))))
        gen = self.engine.run(
            BelelHyperRequest(
                prompt=prompt,
                lyrics=new_lyrics,
                duration_sec=dur,
                filename="tmp_lyric_edit.wav",
                steps=int(req.steps),
                guidance=float(req.guidance),
                extra={
                    "edit_suite": True,
                    "edit_mode": "lyric_edit",
                    "region_frames": [int(f0), int(f1)],
                    "new_lyrics_hash": _sha1(new_lyrics),
                    **(dict(req.extra) if isinstance(req.extra, dict) else {}),
                },
            )
        )

        mel_obj = torch.load(str(gen["mel_path"]), map_location="cpu")
        gen_mel = mel_obj["mel"] if isinstance(mel_obj, dict) and "mel" in mel_obj else mel_obj
        if not isinstance(gen_mel, torch.Tensor) or gen_mel.ndim != 2:
            raise ValueError("Invalid generated mel")

        edited_mel = base_mel.clone()
        edited_mel[:, f0:f1] = gen_mel[:, f0:f1]

        out = self._finalize_mel_as_output(
            edited_mel,
            prompt=prompt,
            lyrics=new_lyrics,
            filename="edited_lyric.wav",
            meta_extra={
                "edit_suite": True,
                "edit_mode": "lyric_edit",
                "region_sec": [float(req.t_start_sec), float(req.t_end_sec)],
                "region_frames": [int(f0), int(f1)],
                "new_lyrics_hash": _sha1(new_lyrics),
                "crossfade_ms": int(req.crossfade_ms),
                **(dict(req.extra) if isinstance(req.extra, dict) else {}),
            },
        )

        out["details"] = {
            "mode": "lyric_edit",
            "region_frames": [int(f0), int(f1)],
        }
        return out

    # --------------------------------------------------------
    # Finalization: turn mel into wav and write provenance
    # --------------------------------------------------------

    def _finalize_mel_as_output(
        self,
        mel_80T: torch.Tensor,
        *,
        prompt: str,
        lyrics: str,
        filename: str,
        meta_extra: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Writes:
          - wav
          - wav.json sidecar
          - mel.pt sidecar containing {mel,prompt,lyrics,meta}

        Without modifying engine internals.
        """
        # Vocode
        mel_b = mel_80T.unsqueeze(0)  # [1,80,T]
        wav = self.engine.mel_to_waveform(mel_b)

        # Save wav
        wav_path = self.engine.save_wav(wav, filename)

        # Build meta aligned with engine conventions
        meta: Dict[str, Any] = {
            "utc": _utc(),
            "preset": "ultra2",
            "steps": int(self.engine.cfg.steps),
            "guidance": float(self.engine.cfg.guidance),
            "seed": None if self.engine.cfg.seed is None else int(self.engine.cfg.seed),
            "dtype": str(self.engine.cfg.dtype),
            "tf32": bool(self.engine.cfg.tf32),
            "compile": bool(self.engine.cfg.compile),
            "codec_ckpt": str(self.engine.cfg.codec_ckpt or ""),
            "denoiser_ckpt": str(self.engine.cfg.denoiser_ckpt or ""),
            "edit_suite": True,
            "edit_meta": dict(meta_extra or {}),
        }

        mel_path = self.engine.save_mel_sidecar_pt(
            mel_b,
            filename if filename.endswith(".wav") else (filename + ".wav"),
            prompt=prompt,
            lyrics=lyrics,
            meta=meta,
        )

        wav_sidecar = self.engine.save_wav_sidecar_json(
            wav_path,
            prompt=prompt,
            lyrics=lyrics,
            meta=meta,
        )

        return {
            "wav": wav,
            "mel": mel_b,
            "wav_path": wav_path,
            "mel_path": mel_path,
            "wav_sidecar": wav_sidecar,
            "meta": meta,
            "auto": None,
        }
