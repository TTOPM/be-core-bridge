# BELEL-SING/belel-sing-gen/belel_editing_suite_ui.py
from __future__ import annotations

import argparse
import json
import os
import time
import hashlib
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import torch
import gradio as gr

from belel_hyper_core.belel_engine import (
    BelelHyperEngine,
    BelelHyperConfig,
    BelelHyperRequest,
)

# Optional: if you want benchmark scoring inside the UI for every edit.
# Keep it off by default; enable with --score_on_save.
from belel_hyper_core.metrics.belel_benchmark_protocol import (
    BelelBenchmarkProtocol,
    BelelBenchmarkGates,
    BelelBenchmarkWeights,
)


# ============================================================
# Small utilities
# ============================================================

def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def _ensure_dir(p: str) -> None:
    Path(p).mkdir(parents=True, exist_ok=True)


def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _safe_write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _sha1_str(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def _sha256_file(path: str) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(x)))


def _as_float(x: Any, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _load_mel_pt(path: Path) -> Tuple[torch.Tensor, str, str, Dict[str, Any]]:
    """
    Returns: mel [80,T], prompt, lyrics, meta
    Accepts:
      - pt containing tensor
      - pt containing dict {"mel": tensor, "prompt": str, "lyrics": str, "meta": dict}
    """
    obj = torch.load(str(path), map_location="cpu")
    if isinstance(obj, dict) and "mel" in obj:
        mel = obj["mel"]
        prompt = str(obj.get("prompt", "") or "")
        lyrics = str(obj.get("lyrics", "") or "")
        meta = obj.get("meta", {}) if isinstance(obj.get("meta", {}), dict) else {}
    else:
        mel = obj
        prompt, lyrics, meta = "", "", {}

    if not isinstance(mel, torch.Tensor):
        raise ValueError(f"mel.pt does not contain a torch.Tensor: {path}")
    if mel.ndim == 3 and mel.shape[0] == 1:
        mel = mel[0]
    if mel.ndim != 2 or mel.shape[0] != 80:
        raise ValueError(f"Expected mel [80,T], got {tuple(mel.shape)} in {path}")
    return mel.float(), prompt, lyrics, dict(meta)


def _load_wav_sidecar_json(path: Path) -> Tuple[str, str, Dict[str, Any]]:
    """
    Returns prompt, lyrics, meta from wav.json
    """
    obj = _safe_read_json(path)
    prompt = str(obj.get("prompt", "") or "")
    lyrics = str(obj.get("lyrics", "") or "")
    meta = obj.get("meta", {}) if isinstance(obj.get("meta", {}), dict) else {}
    # Also bring top-level fields into meta for provenance
    for k, v in obj.items():
        if k not in ("prompt", "lyrics", "meta"):
            meta.setdefault(k, v)
    return prompt, lyrics, meta


def _frames_from_seconds(sec: float, sample_rate: int, hop_length: int) -> int:
    sec = max(0.0, float(sec))
    frames = int((float(sample_rate) * sec) / float(hop_length))
    return max(1, frames)


def _seconds_from_frames(frames: int, sample_rate: int, hop_length: int) -> float:
    return float(frames) * float(hop_length) / float(sample_rate)


def _crossfade_splice(
    base: torch.Tensor,
    insert: torch.Tensor,
    start: int,
    end: int,
    fade: int,
) -> torch.Tensor:
    """
    base: [80,T]
    insert: [80, L] where L == (end-start) ideally; if not, it will be cropped/padded.
    start,end: frame indices in base (0..T)
    fade: frames to crossfade on each boundary (0..)
    """
    if base.ndim != 2 or insert.ndim != 2:
        raise ValueError("Expected base/insert as [80,T] tensors")
    if base.shape[0] != 80 or insert.shape[0] != 80:
        raise ValueError("Expected mel bins == 80")

    T = int(base.shape[1])
    start = _clamp_int(start, 0, T)
    end = _clamp_int(end, start + 1, T)

    target_len = end - start
    ins = insert
    if int(ins.shape[1]) > target_len:
        ins = ins[:, :target_len]
    elif int(ins.shape[1]) < target_len:
        # pad with edge values to avoid sudden silence
        pad_len = target_len - int(ins.shape[1])
        tail = ins[:, -1:].repeat(1, pad_len)
        ins = torch.cat([ins, tail], dim=1)

    out = base.clone()

    # If fade is too large, clamp it
    fade = int(max(0, fade))
    fade = min(fade, target_len // 2, start, T - end)

    # Middle replace (no fade region)
    mid_s = start + fade
    mid_e = end - fade
    if mid_e > mid_s:
        out[:, mid_s:mid_e] = ins[:, fade:target_len - fade]

    # Left fade
    if fade > 0:
        a = out[:, start:start + fade]
        b = ins[:, :fade]
        # ramp 0->1 for insert
        w = torch.linspace(0.0, 1.0, steps=fade, dtype=torch.float32).view(1, -1)
        out[:, start:start + fade] = a * (1.0 - w) + b * w

    # Right fade
    if fade > 0:
        a = out[:, end - fade:end]
        b = ins[:, target_len - fade:target_len]
        w = torch.linspace(1.0, 0.0, steps=fade, dtype=torch.float32).view(1, -1)
        out[:, end - fade:end] = a * (1.0 - w) + b * w

    return out


def _append_extend(
    base: torch.Tensor,
    extension: torch.Tensor,
    fade: int,
) -> torch.Tensor:
    """
    Append extension mel to base with a crossfade overlap of `fade` frames.
    """
    if base.ndim != 2 or extension.ndim != 2:
        raise ValueError("Expected base/extension [80,T]")
    if base.shape[0] != 80 or extension.shape[0] != 80:
        raise ValueError("Expected mel bins == 80")
    T = int(base.shape[1])
    E = int(extension.shape[1])
    fade = int(max(0, fade))
    fade = min(fade, T, E)

    if fade == 0:
        return torch.cat([base, extension], dim=1)

    # Crossfade overlap
    left = base[:, :T - fade]
    a = base[:, T - fade:T]
    b = extension[:, :fade]
    w = torch.linspace(0.0, 1.0, steps=fade, dtype=torch.float32).view(1, -1)
    blend = a * (1.0 - w) + b * w

    right = extension[:, fade:]
    return torch.cat([left, blend, right], dim=1)


# ============================================================
# UI Engine wrapper (single instance)
# ============================================================

class BelelEditingSuite:
    def __init__(
        self,
        *,
        device: str,
        dtype: str,
        codec_ckpt: str,
        denoiser_ckpt: str,
        out_dir: str,
        default_guidance: float = 6.0,
        default_steps: int = 2,
        seed: int = 1234,
        score_on_save: bool = False,
    ):
        self.device = str(device)
        self.dtype = str(dtype)
        self.out_dir = str(out_dir)
        _ensure_dir(self.out_dir)
        _ensure_dir(str(Path(self.out_dir) / "mels"))

        cfg = BelelHyperConfig(
            device=self.device,
            dtype=self.dtype,
            steps=6,
            guidance=float(default_guidance),
            seed=int(seed),
            out_dir=self.out_dir,
            codec_ckpt=codec_ckpt,
            denoiser_ckpt=denoiser_ckpt,
        )

        self.engine = BelelHyperEngine(cfg)
        self.engine.load_checkpoints()
        self.engine.to_device()

        self.default_guidance = float(default_guidance)
        self.default_steps = int(default_steps)
        self.seed = int(seed)

        self.score_on_save = bool(score_on_save)
        self.protocol = None
        if self.score_on_save:
            self.protocol = BelelBenchmarkProtocol(
                gates=BelelBenchmarkGates(),
                weights=BelelBenchmarkWeights(),
            )

        # anchor hashes (for provenance)
        self.ckpt_hashes = {
            "codec_ckpt_path": str(Path(codec_ckpt).resolve()),
            "denoiser_ckpt_path": str(Path(denoiser_ckpt).resolve()),
            "codec_ckpt_sha256": _sha256_file(codec_ckpt),
            "denoiser_ckpt_sha256": _sha256_file(denoiser_ckpt),
        }

    # -------------------------
    # Artifact save (always on)
    # -------------------------

    def _save_edited_artifacts(
        self,
        *,
        mel: torch.Tensor,
        prompt: str,
        lyrics: str,
        base_name: str,
        edit_meta: Dict[str, Any],
    ) -> Tuple[str, str, str, Dict[str, Any]]:
        """
        Writes:
          - wav
          - mel sidecar pt
          - wav sidecar json
        Returns: wav_path, mel_path, wav_sidecar, meta
        """
        # vocode
        wav = self.engine.mel_to_waveform(mel)

        # engine save helpers
        if not base_name.lower().endswith(".wav"):
            base_name += ".wav"

        wav_path = self.engine.save_wav(wav, base_name)

        # Unified meta
        meta = {
            "utc": _utc_now(),
            "edited": True,
            **self.ckpt_hashes,
            **(edit_meta or {}),
        }

        # Save mel sidecar pt (prompt/lyrics/meta inside)
        mel_path = self.engine.save_mel_sidecar_pt(
            mel,
            base_name,
            prompt=prompt,
            lyrics=lyrics,
            meta=meta,
        )

        # Save wav sidecar json (prompt/lyrics/meta inside)
        wav_sidecar = self.engine.save_wav_sidecar_json(
            wav_path,
            prompt=prompt,
            lyrics=lyrics,
            meta=meta,
        )

        # Optional scoring (local gates)
        if self.protocol is not None:
            try:
                score10, passed, breakdown = self.protocol.evaluate(mel, alignment_score=float(meta.get("alignment_score", 0.0)))
                meta["score_10"] = float(score10)
                meta["passed_protocol"] = bool(passed)
                meta["protocol_breakdown"] = breakdown
                # Update mel.pt and wav.json meta with score fields
                torch.save({"mel": mel.detach().float().cpu(), "prompt": prompt, "lyrics": lyrics, "meta": meta}, mel_path)
                _safe_write_json(Path(wav_sidecar), {**_safe_read_json(Path(wav_sidecar)), "meta": meta})
            except Exception:
                pass

        return wav_path, mel_path, wav_sidecar, meta

    # -------------------------
    # Load artifact
    # -------------------------

    def load_source(
        self,
        *,
        mel_pt_file: Optional[str] = None,
        wav_json_file: Optional[str] = None,
    ) -> Tuple[Optional[torch.Tensor], str, str, Dict[str, Any], str]:
        """
        Returns: mel, prompt, lyrics, meta, source_id
        source_id is a stable fingerprint for lineage.
        """
        mel: Optional[torch.Tensor] = None
        prompt = ""
        lyrics = ""
        meta: Dict[str, Any] = {}

        src_bits: List[str] = []

        if mel_pt_file:
            p = Path(mel_pt_file)
            mel, prompt, lyrics, meta = _load_mel_pt(p)
            src_bits.append(f"mel_pt:{p.name}:{_sha1_str(str(p.resolve()))}")

        if wav_json_file:
            jp = Path(wav_json_file)
            p2, l2, m2 = _load_wav_sidecar_json(jp)
            # fallback only; mel.pt remains highest truth
            if not prompt.strip():
                prompt = p2
            if not lyrics.strip():
                lyrics = l2
            # merge: json first, then mel meta overlays
            merged: Dict[str, Any] = {}
            if isinstance(m2, dict):
                merged.update(m2)
            if isinstance(meta, dict):
                merged.update(meta)
            meta = merged
            src_bits.append(f"wav_json:{jp.name}:{_sha1_str(str(jp.resolve()))}")

        source_id = _sha1_str("|".join(src_bits) or f"empty:{_utc_now()}")
        return mel, str(prompt or ""), str(lyrics or ""), dict(meta), source_id

    # -------------------------
    # Core operations
    # -------------------------

    def generate(
        self,
        *,
        prompt: str,
        lyrics: str,
        duration_sec: int,
        steps: int,
        guidance: float,
        seed: int,
        filename: Optional[str],
    ) -> Tuple[str, str, str, Dict[str, Any]]:
        self.engine.cfg.seed = int(seed)

        req = BelelHyperRequest(
            prompt=str(prompt or ""),
            lyrics=str(lyrics or ""),
            duration_sec=int(duration_sec),
            filename=filename,
            steps=int(steps),
            guidance=float(guidance),
            extra={"ui": "editing_suite", "mode": "generate"},
        )
        out = self.engine.run(req)
        return out["wav_path"], out["mel_path"], out["wav_sidecar"], dict(out["meta"])

    def repaint_segment(
        self,
        *,
        base_mel: torch.Tensor,
        prompt: str,
        lyrics: str,
        start_sec: float,
        end_sec: float,
        fade_sec: float,
        steps: int,
        guidance: float,
        seed: int,
        strength: float,
        mode_tag: str,
        source_id: str,
        filename: Optional[str],
        override_prompt: Optional[str] = None,
        override_lyrics: Optional[str] = None,
    ) -> Tuple[str, str, str, Dict[str, Any]]:
        """
        Regenerate ONLY the selected segment duration, then splice into base mel with crossfade.
        strength controls how much we replace:
          1.0 => full replace
          <1.0 => blend old+new in the segment (after splice)
        """
        if base_mel.ndim != 2 or base_mel.shape[0] != 80:
            raise ValueError("base_mel must be [80,T]")

        sr = int(self.engine.cfg.sample_rate)
        hop = int(self.engine.cfg.hop_length)

        T = int(base_mel.shape[1])
        start_f = _frames_from_seconds(float(start_sec), sr, hop)
        end_f = _frames_from_seconds(float(end_sec), sr, hop)
        start_f = _clamp_int(start_f, 0, T - 1)
        end_f = _clamp_int(end_f, start_f + 1, T)

        seg_frames = end_f - start_f
        seg_sec = _seconds_from_frames(seg_frames, sr, hop)

        fade_frames = _frames_from_seconds(float(fade_sec), sr, hop)
        fade_frames = _clamp_int(fade_frames, 0, seg_frames // 2)

        # Conditioning overrides for edit
        p = str((override_prompt if override_prompt is not None else prompt) or "")
        l = str((override_lyrics if override_lyrics is not None else lyrics) or "")

        # Generate new mel for just the segment duration
        self.engine.cfg.seed = int(seed)
        req = BelelHyperRequest(
            prompt=p,
            lyrics=l,
            duration_sec=max(1, int(round(seg_sec))),
            filename=None,
            steps=int(steps),
            guidance=float(guidance),
            extra={"ui": "editing_suite", "mode": mode_tag, "source_id": source_id},
        )
        new_seg_mel = self.engine.generate_mel(req).detach().float().cpu()[0] if False else self.engine.generate_mel(req).detach().float().cpu()
        # engine.generate_mel returns [80,T] already (per your engine code). Keep it consistent.
        if new_seg_mel.ndim == 3 and new_seg_mel.shape[0] == 1:
            new_seg_mel = new_seg_mel[0]
        if new_seg_mel.ndim != 2:
            raise ValueError("generated segment mel unexpected shape")

        # Splice with crossfade
        spliced = _crossfade_splice(base_mel.cpu(), new_seg_mel.cpu(), start_f, end_f, fade_frames)

        # Optional blend old/new across segment (post-splice), controlled by strength
        st = float(max(0.0, min(1.0, strength)))
        if st < 1.0:
            out = spliced.clone()
            seg_old = base_mel[:, start_f:end_f].cpu()
            seg_new = spliced[:, start_f:end_f].cpu()
            out[:, start_f:end_f] = seg_old * (1.0 - st) + seg_new * st
            spliced = out

        # Save artifacts
        base_name = filename or f"belel_edit_{mode_tag}_{_now_tag()}.wav"
        edit_meta = {
            "mode": mode_tag,
            "steps": int(steps),
            "guidance": float(guidance),
            "seed": int(seed),
            "segment": {
                "start_sec": float(start_sec),
                "end_sec": float(end_sec),
                "start_frame": int(start_f),
                "end_frame": int(end_f),
                "fade_sec": float(fade_sec),
                "fade_frames": int(fade_frames),
            },
            "strength": float(st),
            "source_id": str(source_id),
            "source_prompt_hash": _sha1_str(prompt),
            "source_lyrics_hash": _sha1_str(lyrics),
            "edit_prompt_hash": _sha1_str(p),
            "edit_lyrics_hash": _sha1_str(l),
            "edit_lineage": {
                "type": "segment_regen_splice",
                "crossfade": True,
            },
        }

        return self._save_edited_artifacts(
            mel=spliced,
            prompt=p,
            lyrics=l,
            base_name=base_name,
            edit_meta=edit_meta,
        )

    def extend(
        self,
        *,
        base_mel: torch.Tensor,
        prompt: str,
        lyrics: str,
        extend_sec: float,
        fade_sec: float,
        steps: int,
        guidance: float,
        seed: int,
        filename: Optional[str],
        source_id: str,
        override_prompt: Optional[str] = None,
        override_lyrics: Optional[str] = None,
    ) -> Tuple[str, str, str, Dict[str, Any]]:
        if base_mel.ndim != 2 or base_mel.shape[0] != 80:
            raise ValueError("base_mel must be [80,T]")

        extend_sec = float(max(1.0, extend_sec))
        sr = int(self.engine.cfg.sample_rate)
        hop = int(self.engine.cfg.hop_length)
        fade_frames = _frames_from_seconds(float(fade_sec), sr, hop)
        fade_frames = max(0, fade_frames)

        p = str((override_prompt if override_prompt is not None else prompt) or "")
        l = str((override_lyrics if override_lyrics is not None else lyrics) or "")

        self.engine.cfg.seed = int(seed)
        req = BelelHyperRequest(
            prompt=p,
            lyrics=l,
            duration_sec=int(round(extend_sec)),
            filename=None,
            steps=int(steps),
            guidance=float(guidance),
            extra={"ui": "editing_suite", "mode": "extend", "source_id": source_id},
        )
        ext = self.engine.generate_mel(req).detach().float().cpu()
        if ext.ndim == 3 and ext.shape[0] == 1:
            ext = ext[0]
        if ext.ndim != 2:
            raise ValueError("generated extension mel unexpected shape")

        out_mel = _append_extend(base_mel.cpu(), ext.cpu(), fade_frames)

        base_name = filename or f"belel_extend_{_now_tag()}.wav"
        edit_meta = {
            "mode": "extend",
            "steps": int(steps),
            "guidance": float(guidance),
            "seed": int(seed),
            "extend": {
                "extend_sec": float(extend_sec),
                "fade_sec": float(fade_sec),
                "fade_frames": int(fade_frames),
            },
            "source_id": str(source_id),
            "source_prompt_hash": _sha1_str(prompt),
            "source_lyrics_hash": _sha1_str(lyrics),
            "edit_prompt_hash": _sha1_str(p),
            "edit_lyrics_hash": _sha1_str(l),
            "edit_lineage": {"type": "append_crossfade"},
        }

        return self._save_edited_artifacts(
            mel=out_mel,
            prompt=p,
            lyrics=l,
            base_name=base_name,
            edit_meta=edit_meta,
        )


# ============================================================
# Gradio UI (production layout)
# ============================================================

def build_ui(suite: BelelEditingSuite) -> gr.Blocks:
    with gr.Blocks(title="BELEL-SING — Unified Editing Suite", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            "# BELEL-SING — Unified Editing Suite\n"
            "Product-grade editing on BELEL artifacts.\n\n"
            "- Always writes **wav + mel.pt + wav.json**\n"
            "- Segment-safe edits (crossfade splicing)\n"
            "- Edit lineage captured in sidecars\n"
        )

        # Shared state across tabs
        state_mel = gr.State(value=None)       # torch.Tensor [80,T] stored as CPU tensor
        state_prompt = gr.State(value="")
        state_lyrics = gr.State(value="")
        state_meta = gr.State(value={})
        state_source_id = gr.State(value="")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## Load Source Artifact (optional)")
                mel_pt = gr.File(label="Upload mel sidecar (.pt) (preferred)", file_types=[".pt"], type="filepath")
                wav_json = gr.File(label="Upload wav sidecar (.json) (optional fallback)", file_types=[".json"], type="filepath")
                load_btn = gr.Button("Load Source", variant="primary")
                load_info = gr.JSON(label="Loaded Source (preview)", value={})

            with gr.Column(scale=2):
                gr.Markdown("## Working Text Context")
                prompt_box = gr.Textbox(label="Prompt", lines=4, placeholder="Prompt conditioning text")
                lyrics_box = gr.Textbox(label="Lyrics", lines=6, placeholder="Lyrics (optional)")
                meta_box = gr.JSON(label="Meta (read-only; auto written on save)", value={})

        def _load_source(mel_pt_path: Optional[str], wav_json_path: Optional[str]):
            mel, prompt, lyrics, meta, source_id = suite.load_source(
                mel_pt_file=mel_pt_path,
                wav_json_file=wav_json_path,
            )
            info = {
                "source_id": source_id,
                "has_mel": bool(mel is not None),
                "mel_shape": tuple(mel.shape) if mel is not None else None,
                "prompt_len": len(prompt or ""),
                "lyrics_len": len(lyrics or ""),
                "meta_keys": sorted(list(meta.keys()))[:50],
            }
            return (
                mel,
                prompt,
                lyrics,
                meta,
                source_id,
                info,
                prompt,
                lyrics,
                meta,
            )

        load_btn.click(
            _load_source,
            inputs=[mel_pt, wav_json],
            outputs=[state_mel, state_prompt, state_lyrics, state_meta, state_source_id, load_info, prompt_box, lyrics_box, meta_box],
        )

        gr.Markdown("---")

        with gr.Tabs():
            # ========================================================
            # Generate
            # ========================================================
            with gr.Tab("Generate"):
                with gr.Row():
                    with gr.Column(scale=1):
                        duration = gr.Slider(10, 300, value=60, step=1, label="Duration (sec)")
                        steps = gr.Radio([2, 4, 6], value=2, label="Steps")
                        guidance = gr.Slider(1.0, 10.0, value=suite.default_guidance, step=0.1, label="Guidance")
                        seed = gr.Number(value=suite.seed, precision=0, label="Seed (int)")
                        filename = gr.Textbox(value="", label="Output filename (optional)", placeholder="e.g., my_song.wav")
                        gen_btn = gr.Button("Generate", variant="primary")
                    with gr.Column(scale=2):
                        gen_audio = gr.Audio(label="Output Audio", type="filepath")
                        gen_report = gr.JSON(label="Generation Report", value={})

                def _do_generate(prompt: str, lyrics: str, duration_sec: int, steps: int, guidance: float, seed: int, filename: str):
                    fname = filename.strip() if filename and filename.strip() else None
                    wav_path, mel_path, wav_sidecar, meta = suite.generate(
                        prompt=prompt,
                        lyrics=lyrics,
                        duration_sec=int(duration_sec),
                        steps=int(steps),
                        guidance=float(guidance),
                        seed=int(seed),
                        filename=fname,
                    )
                    # Load mel back into state for edits
                    mel, p2, l2, m2 = _load_mel_pt(Path(mel_path))
                    info = {
                        "wav_path": wav_path,
                        "mel_path": mel_path,
                        "wav_sidecar": wav_sidecar,
                        "meta_keys": sorted(list(meta.keys()))[:80],
                    }
                    return wav_path, info, mel, p2 or prompt, l2 or lyrics, m2, _sha1_str(mel_path)

                gen_btn.click(
                    _do_generate,
                    inputs=[prompt_box, lyrics_box, duration, steps, guidance, seed, filename],
                    outputs=[gen_audio, gen_report, state_mel, state_prompt, state_lyrics, state_meta, state_source_id],
                )

            # ========================================================
            # Repaint (segment regen)
            # ========================================================
            with gr.Tab("Repaint"):
                with gr.Row():
                    with gr.Column(scale=1):
                        start_sec = gr.Slider(0, 300, value=5, step=0.1, label="Start (sec)")
                        end_sec = gr.Slider(0, 300, value=15, step=0.1, label="End (sec)")
                        fade_sec = gr.Slider(0.0, 2.0, value=0.35, step=0.05, label="Crossfade (sec)")
                        strength = gr.Slider(0.0, 1.0, value=1.0, step=0.05, label="Replace Strength (0..1)")
                        r_steps = gr.Radio([2, 4, 6], value=2, label="Steps")
                        r_guidance = gr.Slider(1.0, 10.0, value=suite.default_guidance, step=0.1, label="Guidance")
                        r_seed = gr.Number(value=suite.seed + 1, precision=0, label="Seed (int)")
                        r_filename = gr.Textbox(value="", label="Output filename (optional)")
                        repaint_btn = gr.Button("Repaint Segment", variant="primary")
                    with gr.Column(scale=2):
                        repaint_audio = gr.Audio(label="Edited Audio", type="filepath")
                        repaint_report = gr.JSON(label="Edit Report", value={})

                def _do_repaint(
                    mel_state,
                    prompt: str,
                    lyrics: str,
                    start_s: float,
                    end_s: float,
                    fade_s: float,
                    strength_v: float,
                    steps_v: int,
                    guidance_v: float,
                    seed_v: int,
                    filename_v: str,
                    source_id: str,
                ):
                    if mel_state is None:
                        raise gr.Error("No mel loaded. Generate or Load Source first.")
                    base_mel = mel_state
                    fname = filename_v.strip() if filename_v and filename_v.strip() else None

                    wav_path, mel_path, wav_sidecar, meta = suite.repaint_segment(
                        base_mel=base_mel,
                        prompt=prompt,
                        lyrics=lyrics,
                        start_sec=float(start_s),
                        end_sec=float(end_s),
                        fade_sec=float(fade_s),
                        steps=int(steps_v),
                        guidance=float(guidance_v),
                        seed=int(seed_v),
                        strength=float(strength_v),
                        mode_tag="repaint",
                        source_id=str(source_id or ""),
                        filename=fname,
                    )
                    mel, p2, l2, m2 = _load_mel_pt(Path(mel_path))
                    report = {"wav_path": wav_path, "mel_path": mel_path, "wav_sidecar": wav_sidecar, "meta": meta}
                    return wav_path, report, mel, p2 or prompt, l2 or lyrics, m2, _sha1_str(mel_path)

                repaint_btn.click(
                    _do_repaint,
                    inputs=[state_mel, prompt_box, lyrics_box, start_sec, end_sec, fade_sec, strength, r_steps, r_guidance, r_seed, r_filename, state_source_id],
                    outputs=[repaint_audio, repaint_report, state_mel, state_prompt, state_lyrics, state_meta, state_source_id],
                )

            # ========================================================
            # Lyric Edit (segment regen with lyric override)
            # ========================================================
            with gr.Tab("Lyric Edit"):
                with gr.Row():
                    with gr.Column(scale=1):
                        le_start = gr.Slider(0, 300, value=5, step=0.1, label="Start (sec)")
                        le_end = gr.Slider(0, 300, value=15, step=0.1, label="End (sec)")
                        le_fade = gr.Slider(0.0, 2.0, value=0.35, step=0.05, label="Crossfade (sec)")
                        le_strength = gr.Slider(0.0, 1.0, value=1.0, step=0.05, label="Replace Strength (0..1)")
                        le_steps = gr.Radio([2, 4, 6], value=2, label="Steps")
                        le_guidance = gr.Slider(1.0, 10.0, value=suite.default_guidance, step=0.1, label="Guidance")
                        le_seed = gr.Number(value=suite.seed + 2, precision=0, label="Seed (int)")
                        le_filename = gr.Textbox(value="", label="Output filename (optional)")
                        gr.Markdown("### Edited Lyrics (full text)\nSupply the updated lyrics text used for this segment.")
                        lyrics_override = gr.Textbox(label="New Lyrics", lines=6, placeholder="Paste updated lyrics here")
                        lyric_edit_btn = gr.Button("Apply Lyric Edit", variant="primary")
                    with gr.Column(scale=2):
                        lyric_audio = gr.Audio(label="Edited Audio", type="filepath")
                        lyric_report = gr.JSON(label="Edit Report", value={})

                def _do_lyric_edit(
                    mel_state,
                    prompt: str,
                    lyrics: str,
                    start_s: float,
                    end_s: float,
                    fade_s: float,
                    strength_v: float,
                    steps_v: int,
                    guidance_v: float,
                    seed_v: int,
                    filename_v: str,
                    new_lyrics: str,
                    source_id: str,
                ):
                    if mel_state is None:
                        raise gr.Error("No mel loaded. Generate or Load Source first.")
                    base_mel = mel_state
                    fname = filename_v.strip() if filename_v and filename_v.strip() else None
                    nl = (new_lyrics or "").strip()
                    if not nl:
                        raise gr.Error("New Lyrics is empty. Paste the updated lyrics.")

                    wav_path, mel_path, wav_sidecar, meta = suite.repaint_segment(
                        base_mel=base_mel,
                        prompt=prompt,
                        lyrics=lyrics,
                        start_sec=float(start_s),
                        end_sec=float(end_s),
                        fade_sec=float(fade_s),
                        steps=int(steps_v),
                        guidance=float(guidance_v),
                        seed=int(seed_v),
                        strength=float(strength_v),
                        mode_tag="lyric_edit",
                        source_id=str(source_id or ""),
                        filename=fname,
                        override_lyrics=nl,
                    )
                    mel, p2, l2, m2 = _load_mel_pt(Path(mel_path))
                    report = {"wav_path": wav_path, "mel_path": mel_path, "wav_sidecar": wav_sidecar, "meta": meta}
                    return wav_path, report, mel, p2 or prompt, l2 or nl, m2, _sha1_str(mel_path)

                lyric_edit_btn.click(
                    _do_lyric_edit,
                    inputs=[state_mel, prompt_box, lyrics_box, le_start, le_end, le_fade, le_strength, le_steps, le_guidance, le_seed, le_filename, lyrics_override, state_source_id],
                    outputs=[lyric_audio, lyric_report, state_mel, state_prompt, state_lyrics, state_meta, state_source_id],
                )

            # ========================================================
            # Extend
            # ========================================================
            with gr.Tab("Extend"):
                with gr.Row():
                    with gr.Column(scale=1):
                        extend_sec = gr.Slider(1, 240, value=30, step=1, label="Extend by (sec)")
                        ext_fade = gr.Slider(0.0, 2.0, value=0.50, step=0.05, label="Crossfade (sec)")
                        ext_steps = gr.Radio([2, 4, 6], value=2, label="Steps")
                        ext_guidance = gr.Slider(1.0, 10.0, value=suite.default_guidance, step=0.1, label="Guidance")
                        ext_seed = gr.Number(value=suite.seed + 3, precision=0, label="Seed (int)")
                        ext_filename = gr.Textbox(value="", label="Output filename (optional)")
                        extend_btn = gr.Button("Extend", variant="primary")
                    with gr.Column(scale=2):
                        extend_audio = gr.Audio(label="Extended Audio", type="filepath")
                        extend_report = gr.JSON(label="Extend Report", value={})

                def _do_extend(
                    mel_state,
                    prompt: str,
                    lyrics: str,
                    extend_s: float,
                    fade_s: float,
                    steps_v: int,
                    guidance_v: float,
                    seed_v: int,
                    filename_v: str,
                    source_id: str,
                ):
                    if mel_state is None:
                        raise gr.Error("No mel loaded. Generate or Load Source first.")
                    base_mel = mel_state
                    fname = filename_v.strip() if filename_v and filename_v.strip() else None

                    wav_path, mel_path, wav_sidecar, meta = suite.extend(
                        base_mel=base_mel,
                        prompt=prompt,
                        lyrics=lyrics,
                        extend_sec=float(extend_s),
                        fade_sec=float(fade_s),
                        steps=int(steps_v),
                        guidance=float(guidance_v),
                        seed=int(seed_v),
                        filename=fname,
                        source_id=str(source_id or ""),
                    )
                    mel, p2, l2, m2 = _load_mel_pt(Path(mel_path))
                    report = {"wav_path": wav_path, "mel_path": mel_path, "wav_sidecar": wav_sidecar, "meta": meta}
                    return wav_path, report, mel, p2 or prompt, l2 or lyrics, m2, _sha1_str(mel_path)

                extend_btn.click(
                    _do_extend,
                    inputs=[state_mel, prompt_box, lyrics_box, extend_sec, ext_fade, ext_steps, ext_guidance, ext_seed, ext_filename, state_source_id],
                    outputs=[extend_audio, extend_report, state_mel, state_prompt, state_lyrics, state_meta, state_source_id],
                )

            # ========================================================
            # Retake (segment regen; seed jitter; optional prompt tweak)
            # ========================================================
            with gr.Tab("Retake"):
                with gr.Row():
                    with gr.Column(scale=1):
                        rt_start = gr.Slider(0, 300, value=5, step=0.1, label="Start (sec)")
                        rt_end = gr.Slider(0, 300, value=15, step=0.1, label="End (sec)")
                        rt_fade = gr.Slider(0.0, 2.0, value=0.35, step=0.05, label="Crossfade (sec)")
                        rt_strength = gr.Slider(0.0, 1.0, value=1.0, step=0.05, label="Replace Strength (0..1)")
                        rt_steps = gr.Radio([2, 4, 6], value=2, label="Steps")
                        rt_guidance = gr.Slider(1.0, 10.0, value=suite.default_guidance, step=0.1, label="Guidance")
                        rt_seed = gr.Number(value=suite.seed + 4, precision=0, label="Seed (int)")
                        rt_jitter = gr.Number(value=11, precision=0, label="Seed Jitter (+/-)")
                        rt_filename = gr.Textbox(value="", label="Output filename (optional)")
                        prompt_tweak = gr.Textbox(
                            label="Retake Prompt Tweak (optional)",
                            lines=2,
                            placeholder="Optional: add a short instruction for the retake segment only",
                        )
                        retake_btn = gr.Button("Retake Segment", variant="primary")
                    with gr.Column(scale=2):
                        retake_audio = gr.Audio(label="Retake Audio", type="filepath")
                        retake_report = gr.JSON(label="Retake Report", value={})

                def _do_retake(
                    mel_state,
                    prompt: str,
                    lyrics: str,
                    start_s: float,
                    end_s: float,
                    fade_s: float,
                    strength_v: float,
                    steps_v: int,
                    guidance_v: float,
                    seed_v: int,
                    jitter_v: int,
                    filename_v: str,
                    tweak: str,
                    source_id: str,
                ):
                    if mel_state is None:
                        raise gr.Error("No mel loaded. Generate or Load Source first.")
                    base_mel = mel_state
                    fname = filename_v.strip() if filename_v and filename_v.strip() else None

                    base_seed = int(seed_v)
                    j = int(abs(jitter_v))
                    # deterministic jitter pattern: alternate +j, -j by time tag
                    salt = int(time.time()) % 2
                    seed2 = base_seed + (j if salt == 0 else -j)

                    tweak_txt = (tweak or "").strip()
                    if tweak_txt:
                        p_override = (prompt or "").strip() + "\n\nRETAAAAKE:\n" + tweak_txt
                    else:
                        p_override = None

                    wav_path, mel_path, wav_sidecar, meta = suite.repaint_segment(
                        base_mel=base_mel,
                        prompt=prompt,
                        lyrics=lyrics,
                        start_sec=float(start_s),
                        end_sec=float(end_s),
                        fade_sec=float(fade_s),
                        steps=int(steps_v),
                        guidance=float(guidance_v),
                        seed=int(seed2),
                        strength=float(strength_v),
                        mode_tag="retake",
                        source_id=str(source_id or ""),
                        filename=fname,
                        override_prompt=p_override,
                    )
                    mel, p2, l2, m2 = _load_mel_pt(Path(mel_path))
                    report = {"wav_path": wav_path, "mel_path": mel_path, "wav_sidecar": wav_sidecar, "meta": meta}
                    return wav_path, report, mel, p2 or prompt, l2 or lyrics, m2, _sha1_str(mel_path)

                retake_btn.click(
                    _do_retake,
                    inputs=[state_mel, prompt_box, lyrics_box, rt_start, rt_end, rt_fade, rt_strength, rt_steps, rt_guidance, rt_seed, rt_jitter, rt_filename, prompt_tweak, state_source_id],
                    outputs=[retake_audio, retake_report, state_mel, state_prompt, state_lyrics, state_meta, state_source_id],
                )

        # Footer
        gr.Markdown(
            "### Output Discipline\n"
            "- Every operation writes: **.wav + mels/.pt + .json**\n"
            "- Sidecars include edit lineage, segment bounds, fade, seed, steps, guidance, and checkpoint hashes.\n"
        )

    return demo


# ============================================================
# Entrypoint
# ============================================================

def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--codec_ckpt", required=True)
    ap.add_argument("--denoiser_ckpt", required=True)
    ap.add_argument("--out_dir", default="outputs/belel_editing_suite")

    ap.add_argument("--default_steps", type=int, default=2, choices=[2, 4, 6])
    ap.add_argument("--default_guidance", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=1234)

    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--share", action="store_true")

    ap.add_argument("--score_on_save", action="store_true", help="Run BelelBenchmarkProtocol after each save (slower).")

    args = ap.parse_args()

    suite = BelelEditingSuite(
        device=args.device,
        dtype=args.dtype,
        codec_ckpt=args.codec_ckpt,
        denoiser_ckpt=args.denoiser_ckpt,
        out_dir=args.out_dir,
        default_guidance=float(args.default_guidance),
        default_steps=int(args.default_steps),
        seed=int(args.seed),
        score_on_save=bool(args.score_on_save),
    )

    ui = build_ui(suite)
    ui.launch(server_name=args.host, server_port=int(args.port), share=bool(args.share))


if __name__ == "__main__":
    main()