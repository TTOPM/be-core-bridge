# BELEL-SING/belel-sing-gen/belel_hyper_core/editing/belel_edit_ops.py
from __future__ import annotations

import json
import math
import hashlib
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Literal, List, Union

import torch


# ============================================================
# Edit Types
# ============================================================

EditType = Literal["repaint", "extend", "retake", "lyric_edit"]


# ============================================================
# Core Edit Request / Result
# ============================================================

@dataclass
class BelelEditRequest:
    """
    Canonical edit request.

    Philosophy:
      - Non-destructive: edits create a new artifact + provenance chain
      - Deterministic: stable hashes for caching and reproducibility
      - Minimal: edit operations focus on mel/latent stability first

    Fields:
      src_wav: optional source wav path (for UI workflows)
      src_mel_pt: required source mel sidecar .pt path (Belel format dict: {"mel":..., "prompt":..., "lyrics":..., "meta":...})
      edit_type: repaint | extend | retake | lyric_edit

      start_sec/end_sec: region to edit for repaint / lyric_edit
      extend_sec: amount to extend for extend

      new_prompt/new_lyrics: overrides (lyric_edit uses new_lyrics, retake can optionally tweak prompt/lyrics)
      seed_delta: deterministic delta applied to base seed (retake, repaint retries)
      guidance_override: optional override for guidance
      steps_override: optional override for steps (normally remains 2 in ultra mode)

      crossfade_sec: length of crossfade at boundaries (mel-domain)
      strength: repaint strength in [0..1] (how much to overwrite region)
      attempt: attempt index for auto-retake loops
    """
    src_mel_pt: str
    edit_type: EditType

    # Optional for UI / export only
    src_wav: Optional[str] = None

    # Region selection
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None

    # Extend
    extend_sec: Optional[float] = None

    # Text overrides
    new_prompt: Optional[str] = None
    new_lyrics: Optional[str] = None

    # Inference controls
    seed_delta: int = 0
    guidance_override: Optional[float] = None
    steps_override: Optional[int] = None

    # Stitching / repaint controls
    crossfade_sec: float = 0.35
    strength: float = 1.0

    # Auto-controller bookkeeping
    attempt: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.src_mel_pt:
            raise ValueError("src_mel_pt is required")
        if self.edit_type not in ("repaint", "extend", "retake", "lyric_edit"):
            raise ValueError(f"Unsupported edit_type: {self.edit_type}")

        if self.edit_type in ("repaint", "lyric_edit"):
            if self.start_sec is None or self.end_sec is None:
                raise ValueError(f"{self.edit_type} requires start_sec and end_sec")
            if float(self.end_sec) <= float(self.start_sec):
                raise ValueError("end_sec must be > start_sec")

        if self.edit_type == "extend":
            if self.extend_sec is None or float(self.extend_sec) <= 0:
                raise ValueError("extend requires extend_sec > 0")

        if self.crossfade_sec < 0:
            raise ValueError("crossfade_sec must be >= 0")

        self.strength = float(max(0.0, min(1.0, float(self.strength))))


@dataclass
class BelelEditResult:
    """
    Output of an edit op (mel-level).
    Engine layer will convert mel->wav and write sidecars.
    """
    mel: torch.Tensor                     # [80, T] float32
    prompt: str
    lyrics: str
    meta: Dict[str, Any]
    edit_meta: Dict[str, Any]


# ============================================================
# Provenance / Hashing
# ============================================================

def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha1_str(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def _stable_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def make_edit_id(req: BelelEditRequest, src_meta: Dict[str, Any]) -> str:
    """
    Deterministic edit id for caching and artifact naming.

    Includes:
      - src mel path name
      - edit request canonical JSON
      - src meta hashes (prompt/lyrics hashes if present)
    """
    src_name = Path(req.src_mel_pt).name
    payload = {
        "src": src_name,
        "edit": asdict(req),
        "src_meta_hint": {
            "preset": str(src_meta.get("preset", "")),
            "steps": int(src_meta.get("steps", 0)) if str(src_meta.get("steps", "")).isdigit() else src_meta.get("steps", ""),
            "guidance": float(src_meta.get("guidance", 0.0)) if _is_number(src_meta.get("guidance")) else src_meta.get("guidance", ""),
            "prompt_hash": str(src_meta.get("prompt_hash", "")) or "",
            "lyrics_hash": str(src_meta.get("lyrics_hash", "")) or "",
        },
    }
    return _sha1_str(_stable_json(payload))


def _is_number(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


# ============================================================
# Mel IO (Belel sidecar format)
# ============================================================

def load_belel_mel_pt(path: Union[str, Path]) -> Tuple[torch.Tensor, str, str, Dict[str, Any]]:
    """
    Loads Belel mel sidecar .pt.

    Accepts:
      - dict: {"mel": Tensor[80,T], "prompt": str, "lyrics": str, "meta": dict}
      - tensor: Tensor[80,T] (prompt/lyrics/meta empty)
    """
    p = Path(path)
    obj = torch.load(str(p), map_location="cpu")

    prompt = ""
    lyrics = ""
    meta: Dict[str, Any] = {}

    if isinstance(obj, dict) and "mel" in obj:
        mel = obj["mel"]
        prompt = str(obj.get("prompt", "") or "")
        lyrics = str(obj.get("lyrics", "") or "")
        m = obj.get("meta", {})
        meta = dict(m) if isinstance(m, dict) else {}
    elif isinstance(obj, torch.Tensor):
        mel = obj
    else:
        raise ValueError(f"Unsupported mel pt format: {p}")

    if not isinstance(mel, torch.Tensor):
        raise ValueError(f"Mel payload not tensor: {p}")

    mel = mel.float()
    if mel.ndim != 2 or mel.shape[0] != 80:
        raise ValueError(f"Expected mel [80,T], got {tuple(mel.shape)} in {p}")

    return mel, prompt, lyrics, meta


# ============================================================
# Time / Index mapping
# ============================================================

@dataclass
class BelelTimebase:
    """
    Defines conversions between seconds, mel frames, and latent indices.

    Defaults should match your engine config:
      - sample_rate=22050
      - hop_length=256  => mel frames/sec ≈ 86.1328

    Latent downsample ratio:
      - In engine: latent_T ≈ frames // 4
      - So latent step corresponds to 4 mel frames.
    """
    sample_rate: int = 22050
    hop_length: int = 256
    latent_downsample: int = 4

    def frames_per_sec(self) -> float:
        return float(self.sample_rate) / float(self.hop_length)

    def sec_to_mel_frame(self, sec: float) -> int:
        return int(round(float(sec) * self.frames_per_sec()))

    def mel_frame_to_sec(self, frame: int) -> float:
        return float(frame) / self.frames_per_sec()

    def mel_frame_to_latent_index(self, frame: int) -> int:
        return int(frame // int(self.latent_downsample))

    def latent_index_to_mel_frame(self, idx: int) -> int:
        return int(idx) * int(self.latent_downsample)


def clamp_region(a: int, b: int, T: int) -> Tuple[int, int]:
    a = max(0, min(int(a), int(T)))
    b = max(0, min(int(b), int(T)))
    if b < a:
        a, b = b, a
    return a, b


# ============================================================
# Stitching / Crossfade (mel-domain)
# ============================================================

def _cosine_fade(n: int, *, device: str = "cpu") -> torch.Tensor:
    """
    Cosine ramp from 0->1 over n steps.
    """
    if n <= 0:
        return torch.zeros((0,), dtype=torch.float32, device=device)
    t = torch.linspace(0.0, 1.0, steps=n, device=device, dtype=torch.float32)
    w = 0.5 - 0.5 * torch.cos(math.pi * t)  # 0..1
    return w


def crossfade_mel(
    left: torch.Tensor,
    mid: torch.Tensor,
    right: torch.Tensor,
    *,
    fade_frames: int,
) -> torch.Tensor:
    """
    Stitches [left | mid | right] with cosine crossfades at boundaries.

    All inputs are [80, T?].
    If fade_frames==0 => hard concat.
    """
    if left.ndim != 2 or mid.ndim != 2 or right.ndim != 2:
        raise ValueError("crossfade_mel expects 2D tensors [80,T]")
    if left.shape[0] != 80 or mid.shape[0] != 80 or right.shape[0] != 80:
        raise ValueError("crossfade_mel expects mel bins=80")

    fade = int(max(0, fade_frames))
    if fade == 0:
        return torch.cat([left, mid, right], dim=1)

    # Ensure boundaries have enough frames; if not, reduce fade
    fade = min(fade, left.shape[1], mid.shape[1], right.shape[1])

    device = left.device
    w = _cosine_fade(fade, device=str(device))  # [fade]
    w = w.view(1, -1)  # [1,fade]

    # left-mid blend
    left_keep = left[:, :-fade] if left.shape[1] > fade else left[:, :0]
    left_tail = left[:, -fade:]
    mid_head = mid[:, :fade]
    mid_body = mid[:, fade:-fade] if mid.shape[1] > 2 * fade else mid[:, :0]
    mid_tail = mid[:, -fade:] if mid.shape[1] >= fade else mid[:, :0]

    blend_lm = left_tail * (1.0 - w) + mid_head * w

    # mid-right blend
    right_head = right[:, :fade]
    right_keep = right[:, fade:] if right.shape[1] > fade else right[:, :0]
    blend_mr = mid_tail * (1.0 - w) + right_head * w

    return torch.cat([left_keep, blend_lm, mid_body, blend_mr, right_keep], dim=1)


def apply_strength(
    original: torch.Tensor,
    edited: torch.Tensor,
    *,
    strength: float,
) -> torch.Tensor:
    """
    Linear blend: (1-strength)*original + strength*edited
    strength=1 => full overwrite
    """
    s = float(max(0.0, min(1.0, float(strength))))
    if s >= 0.999:
        return edited
    if s <= 0.001:
        return original
    return original * (1.0 - s) + edited * s


# ============================================================
# Region extraction helpers
# ============================================================

def split_mel_region(
    mel: torch.Tensor,
    *,
    start_frame: int,
    end_frame: int,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Returns (left, mid, right) where mid is [start_frame:end_frame].
    """
    T = int(mel.shape[1])
    a, b = clamp_region(start_frame, end_frame, T)
    left = mel[:, :a]
    mid = mel[:, a:b]
    right = mel[:, b:]
    return left, mid, right


def compute_fade_frames(
    crossfade_sec: float,
    *,
    tb: BelelTimebase,
) -> int:
    frames = int(round(float(crossfade_sec) * tb.frames_per_sec()))
    return max(0, frames)


# ============================================================
# Edit op scaffolds (mel-level)
# ============================================================

def build_edit_meta(
    req: BelelEditRequest,
    *,
    src_prompt: str,
    src_lyrics: str,
    src_meta: Dict[str, Any],
    timebase: BelelTimebase,
) -> Dict[str, Any]:
    """
    Creates an edit provenance dict that gets embedded into output meta.
    """
    src_hash = _sha1_str(str(Path(req.src_mel_pt).resolve()))
    edit_id = make_edit_id(req, src_meta)

    region = {}
    if req.start_sec is not None and req.end_sec is not None:
        region = {
            "start_sec": float(req.start_sec),
            "end_sec": float(req.end_sec),
            "start_frame": int(timebase.sec_to_mel_frame(float(req.start_sec))),
            "end_frame": int(timebase.sec_to_mel_frame(float(req.end_sec))),
        }

    if req.extend_sec is not None:
        region["extend_sec"] = float(req.extend_sec)

    return {
        "utc": _utc_now(),
        "edit_id": edit_id,
        "edit_type": req.edit_type,
        "src_mel_pt": str(req.src_mel_pt),
        "src_wav": str(req.src_wav or ""),
        "src_hash": src_hash,
        "src_prompt_hash": _sha1_str(src_prompt or ""),
        "src_lyrics_hash": _sha1_str(src_lyrics or "") if (src_lyrics or "") else "",
        "seed_delta": int(req.seed_delta),
        "guidance_override": None if req.guidance_override is None else float(req.guidance_override),
        "steps_override": None if req.steps_override is None else int(req.steps_override),
        "crossfade_sec": float(req.crossfade_sec),
        "strength": float(req.strength),
        "attempt": int(req.attempt),
        "region": region,
        "extra": dict(req.extra or {}),
    }


def resolve_text_overrides(
    src_prompt: str,
    src_lyrics: str,
    req: BelelEditRequest,
) -> Tuple[str, str]:
    """
    Rules:
      - retake can override prompt/lyrics if provided
      - lyric_edit must use new_lyrics if provided, otherwise keeps src
      - repaint/extend keep src unless override is explicitly set
    """
    prompt = src_prompt
    lyrics = src_lyrics

    if req.new_prompt is not None:
        prompt = str(req.new_prompt or "")

    if req.edit_type == "lyric_edit":
        if req.new_lyrics is not None:
            lyrics = str(req.new_lyrics or "")
    else:
        # repaint/extend/retake allow optional lyric override too
        if req.new_lyrics is not None:
            lyrics = str(req.new_lyrics or "")

    return prompt, lyrics


# ============================================================
# Simple deterministic region-plan (future: aligner-driven)
# ============================================================

def plan_edit_region_frames(
    req: BelelEditRequest,
    mel_T: int,
    *,
    tb: BelelTimebase,
) -> Tuple[int, int]:
    """
    Converts requested seconds to mel frames and clamps to [0, T].

    NOTE:
      - This is intentionally deterministic and simple.
      - The "10-years-ahead" version will replace this with aligner-driven segment targeting,
        but this contract stays stable.
    """
    if req.start_sec is None or req.end_sec is None:
        return 0, 0
    a = tb.sec_to_mel_frame(float(req.start_sec))
    b = tb.sec_to_mel_frame(float(req.end_sec))
    return clamp_region(a, b, int(mel_T))


# ============================================================
# Public "edit contract" helpers used by edit engine
# ============================================================

def load_edit_source(req: BelelEditRequest) -> Tuple[torch.Tensor, str, str, Dict[str, Any]]:
    """
    Loads source mel+text+meta.
    """
    mel, prompt, lyrics, meta = load_belel_mel_pt(req.src_mel_pt)
    return mel, prompt, lyrics, meta


def make_repaint_inputs(
    src_mel: torch.Tensor,
    req: BelelEditRequest,
    *,
    tb: BelelTimebase,
) -> Dict[str, Any]:
    """
    Extracts region and calculates fade frames.
    """
    T = int(src_mel.shape[1])
    a, b = plan_edit_region_frames(req, T, tb=tb)
    left, mid, right = split_mel_region(src_mel, start_frame=a, end_frame=b)
    fade = compute_fade_frames(req.crossfade_sec, tb=tb)
    return {
        "start_frame": int(a),
        "end_frame": int(b),
        "left": left,
        "mid": mid,
        "right": right,
        "fade_frames": int(fade),
    }


def stitch_repaint(
    src_left: torch.Tensor,
    new_mid: torch.Tensor,
    src_right: torch.Tensor,
    *,
    fade_frames: int,
    strength: float,
) -> torch.Tensor:
    """
    Applies strength blend inside mid before stitching.
    new_mid must match src_mid length (frames).
    """
    if new_mid.ndim != 2 or new_mid.shape[0] != 80:
        raise ValueError("new_mid must be mel [80,Tmid]")

    # In caller: you ensure new_mid length matches src_mid.
    # Strength blending is applied only on the mid segment.
    # For boundary smoothness, crossfade occurs at concat points.

    stitched = crossfade_mel(src_left, new_mid, src_right, fade_frames=int(fade_frames))
    return stitched


def extend_plan(
    src_mel: torch.Tensor,
    req: BelelEditRequest,
    *,
    tb: BelelTimebase,
) -> Dict[str, Any]:
    """
    Computes how many frames to extend.
    """
    if req.extend_sec is None:
        raise ValueError("extend_plan requires extend_sec")

    add_frames = int(round(float(req.extend_sec) * tb.frames_per_sec()))
    add_frames = max(1, add_frames)
    fade = compute_fade_frames(req.crossfade_sec, tb=tb)

    return {
        "add_frames": int(add_frames),
        "fade_frames": int(fade),
    }


# ============================================================
# Naming / artifact helpers (UI + automation)
# ============================================================

def default_edit_filename(
    *,
    src_name: str,
    edit_id: str,
    edit_type: str,
    ext: str = ".wav",
) -> str:
    """
    Deterministic, human-readable filename:
      <srcstem>__<edit_type>__<edit_id[:10]>.wav
    """
    stem = Path(src_name).stem
    short = str(edit_id)[:10]
    if not ext.startswith("."):
        ext = "." + ext
    return f"{stem}__{edit_type}__{short}{ext}"


def write_edit_receipt_json(path: Union[str, Path], payload: Dict[str, Any]) -> str:
    """
    Writes a small JSON receipt for the UI/controller.
    This is separate from wav sidecar; it’s an edit-chain record.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


# ============================================================
# Minimal self-test (optional)
# ============================================================

def _self_test() -> None:
    """
    Lightweight shape tests without external deps.
    """
    tb = BelelTimebase()
    mel = torch.randn(80, 1000)
    left, mid, right = split_mel_region(mel, start_frame=200, end_frame=400)
    out = crossfade_mel(left, mid, right, fade_frames=32)
    assert out.shape[0] == 80
    assert out.shape[1] == 1000

    req = BelelEditRequest(src_mel_pt="x.pt", edit_type="repaint", start_sec=1.0, end_sec=2.0)
    req.validate()
    assert compute_fade_frames(req.crossfade_sec, tb=tb) >= 0


if __name__ == "__main__":
    _self_test()
    print("belel_edit_ops self-test: OK")