# BELEL-SING/belel-sing-gen/belel_hyper_core/editing/belel_edit_ops.py
from __future__ import annotations

import json
import math
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union

import torch


# ============================================================
# Core data contracts
# ============================================================

@dataclass
class BelelTimebase:
    """
    Single authoritative timebase for BELEL-SING editing.

    This must match your vocoder/engine hop_length contract.
    If you change hop_length in the engine, update here too.

    frames_per_sec = sample_rate / hop_length
    """
    sample_rate: int = 22050
    hop_length: int = 256

    def frames_per_sec(self) -> float:
        return float(self.sample_rate) / float(self.hop_length)

    def sec_to_mel_frame(self, sec: float) -> int:
        return int(round(max(0.0, float(sec)) * self.frames_per_sec()))

    def mel_frame_to_sec(self, frame: int) -> float:
        return float(max(0, int(frame))) / self.frames_per_sec()


@dataclass
class BelelEditRequest:
    """
    Unified edit request.

    edit_type:
      - "repaint": regenerate a region (start_sec..end_sec)
      - "extend": extend by extend_sec
      - "retake": full retake (same duration as source)
      - "lyric_edit": update lyrics and optionally repaint region

    src_mel_pt is required and must point to a mel sidecar .pt written by Belel engine:
      {"mel": [80,T], "prompt": str, "lyrics": str, "meta": {...}}

    src_wav is optional (used for receipt provenance + future UI playback linkage).
    """
    edit_type: str
    src_mel_pt: str
    src_wav: Optional[str] = None

    # text overrides
    prompt_override: Optional[str] = None
    lyrics_override: Optional[str] = None

    # region params (repaint / lyric_edit-with-region)
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None

    # extend params
    extend_sec: Optional[float] = None

    # blend control (0..1): 1.0 = full new content, 0.2 = gentle correction
    strength: float = 1.0

    # deterministic perturbations
    seed_delta: int = 0
    attempt: int = 0

    # optional inference overrides (advanced users / UI presets)
    steps_override: Optional[int] = None
    guidance_override: Optional[float] = None

    # optional bag for future controls (fade_sec, align scores, UI tags, etc)
    extra: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        et = str(self.edit_type or "").strip().lower()
        if et not in ("repaint", "extend", "retake", "lyric_edit"):
            raise ValueError(f"Invalid edit_type: {self.edit_type}")

        p = Path(str(self.src_mel_pt or ""))
        if not p.exists():
            raise FileNotFoundError(f"src_mel_pt not found: {p}")

        s = float(self.strength)
        if not (0.0 <= s <= 1.0):
            raise ValueError(f"strength must be in [0..1], got {self.strength}")

        if et in ("repaint", "lyric_edit"):
            # lyric_edit can be text-only; region optional there
            if et == "repaint":
                if self.start_sec is None or self.end_sec is None:
                    raise ValueError("repaint requires start_sec and end_sec")
                a = float(self.start_sec)
                b = float(self.end_sec)
                if not (b > a):
                    raise ValueError("repaint requires end_sec > start_sec")

        if et == "extend":
            if self.extend_sec is None:
                raise ValueError("extend requires extend_sec")
            if float(self.extend_sec) <= 0.0:
                raise ValueError("extend requires extend_sec > 0")

        if self.steps_override is not None:
            so = int(self.steps_override)
            if so not in (2, 4, 6):
                raise ValueError("steps_override must be one of 2,4,6")

        if self.guidance_override is not None:
            g = float(self.guidance_override)
            if g <= 0.0:
                raise ValueError("guidance_override must be > 0")


@dataclass
class BelelEditResult:
    """
    In-memory result object (prior to persistence).
    """
    mel: torch.Tensor          # [80,T] float
    prompt: str
    lyrics: str
    meta: Dict[str, Any]       # merged + updated
    edit_meta: Dict[str, Any]  # edit-chain + benchmark outcome


# ============================================================
# Utilities (strict, deterministic)
# ============================================================

def _sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def _sha1_str(s: str) -> str:
    return _sha1_bytes((s or "").encode("utf-8"))


def _safe_str(x: Any) -> str:
    try:
        return str(x or "")
    except Exception:
        return ""


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _to_mel_2d(obj: Any) -> torch.Tensor:
    """
    Accepts:
      - Tensor [80,T]
      - dict {"mel": Tensor[80,T], ...}
      - Tensor [1,80,T] (squeezed)
    """
    if isinstance(obj, dict) and "mel" in obj:
        obj = obj["mel"]
    if not isinstance(obj, torch.Tensor):
        raise ValueError("mel object is not a torch.Tensor")

    t = obj.float()
    if t.ndim == 3 and t.shape[0] == 1:
        t = t[0]
    if t.ndim != 2 or int(t.shape[0]) != 80:
        raise ValueError(f"Expected mel [80,T], got {tuple(t.shape)}")
    return t


def _cosine_fade(n: int, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    """
    Cosine fade 0..1, shape [1,n]
    """
    if n <= 0:
        return torch.zeros((1, 0), device=device, dtype=dtype)
    t = torch.linspace(0.0, 1.0, steps=int(n), device=device, dtype=torch.float32).view(1, -1)
    w = 0.5 - 0.5 * torch.cos(math.pi * t)
    return w.to(dtype)


def apply_strength(src: torch.Tensor, gen: torch.Tensor, strength: float) -> torch.Tensor:
    """
    Linear blend:
      out = (1-s)*src + s*gen
    """
    src = _to_mel_2d(src)
    gen = _to_mel_2d(gen)

    s = float(max(0.0, min(1.0, float(strength))))
    if src.shape != gen.shape:
        # deterministic length arbitration: match to src
        T = int(src.shape[1])
        if gen.shape[1] < T:
            reps = int(math.ceil(T / max(1, int(gen.shape[1]))))
            gen = gen.repeat(1, reps)[:, :T]
        else:
            gen = gen[:, :T]
    return (src * (1.0 - s) + gen * s).float()


def clamp_region(
    *,
    start_sec: float,
    end_sec: float,
    duration_sec: float,
    min_len_sec: float = 0.05,
) -> Tuple[float, float]:
    """
    Clamp to [0,duration], enforce a minimal region length.
    """
    dur = max(0.0, float(duration_sec))
    a = max(0.0, min(dur, float(start_sec)))
    b = max(0.0, min(dur, float(end_sec)))

    if b <= a:
        # enforce minimal positive region
        b = min(dur, a + float(min_len_sec))

    # if duration is tiny, allow 0..dur
    if dur > 0.0 and b <= a:
        a = 0.0
        b = dur

    return float(a), float(b)


# ============================================================
# Source loading + text resolution
# ============================================================

def load_edit_source(req: BelelEditRequest) -> Tuple[torch.Tensor, str, str, Dict[str, Any]]:
    """
    Loads the source mel + embedded text/meta.

    Returns:
      src_mel: [80,T] float32
      src_prompt: str
      src_lyrics: str
      src_meta: dict
    """
    p = Path(req.src_mel_pt)
    obj = torch.load(str(p), map_location="cpu")

    mel = _to_mel_2d(obj)

    if isinstance(obj, dict):
        prompt = _safe_str(obj.get("prompt", ""))
        lyrics = _safe_str(obj.get("lyrics", ""))
        meta = obj.get("meta", {})
        meta = meta if isinstance(meta, dict) else {}
    else:
        prompt, lyrics, meta = "", "", {}

    # bake minimal source facts for downstream receipts
    src_meta = dict(meta)
    src_meta.setdefault("src_mel_pt", str(p.resolve()))
    if req.src_wav:
        src_meta.setdefault("src_wav", str(Path(req.src_wav).resolve()))

    # duration derived from mel length is more reliable for editing than any declared duration
    src_meta.setdefault("mel_frames", int(mel.shape[1]))

    return mel, prompt, lyrics, src_meta


def resolve_text_overrides(src_prompt: str, src_lyrics: str, req: BelelEditRequest) -> Tuple[str, str]:
    """
    Outputs:
      prompt, lyrics

    Rule:
      - override wins if provided and non-empty after strip
      - else inherit from source
    """
    p = _safe_str(req.prompt_override) if (req.prompt_override is not None) else ""
    l = _safe_str(req.lyrics_override) if (req.lyrics_override is not None) else ""

    out_prompt = p if p.strip() else _safe_str(src_prompt)
    out_lyrics = l if l.strip() else _safe_str(src_lyrics)
    return out_prompt, out_lyrics


# ============================================================
# Edit meta + deterministic IDs
# ============================================================

def make_edit_id(req: BelelEditRequest, src_meta: Dict[str, Any]) -> str:
    """
    Deterministic edit id. Must remain stable across machines.

    Includes:
      - src mel stem + hashes
      - edit type
      - region/extend params
      - text override hashes
      - seed_delta + attempt
      - inference overrides
    """
    src_pt = Path(req.src_mel_pt)
    stem = src_pt.stem

    # stable-ish source signature
    # (prefer hash stored in meta if your engine provides it; else use path stem)
    src_sig = _safe_str(src_meta.get("prompt_hash", "")) + "|" + _safe_str(src_meta.get("lyrics_hash", ""))

    region = ""
    if req.start_sec is not None and req.end_sec is not None:
        region = f"{float(req.start_sec):.4f}:{float(req.end_sec):.4f}"

    extend = ""
    if req.extend_sec is not None:
        extend = f"{float(req.extend_sec):.4f}"

    payload = "|".join(
        [
            f"src:{stem}",
            f"srcsig:{src_sig}",
            f"type:{_safe_str(req.edit_type).lower()}",
            f"region:{region}",
            f"extend:{extend}",
            f"strength:{float(req.strength):.4f}",
            f"pov:{_sha1_str(_safe_str(req.prompt_override) if req.prompt_override else '')}",
            f"lov:{_sha1_str(_safe_str(req.lyrics_override) if req.lyrics_override else '')}",
            f"seed_delta:{int(req.seed_delta)}",
            f"attempt:{int(req.attempt)}",
            f"steps:{int(req.steps_override) if req.steps_override is not None else 0}",
            f"guidance:{float(req.guidance_override) if req.guidance_override is not None else 0.0}",
        ]
    )
    return _sha1_str(payload)


def build_edit_meta(
    req: BelelEditRequest,
    *,
    src_prompt: str,
    src_lyrics: str,
    src_meta: Dict[str, Any],
    timebase: BelelTimebase,
) -> Dict[str, Any]:
    """
    Constructs the authoritative edit meta chain.

    This is persisted into:
      - output mel pt meta["edit"]
      - output wav sidecar meta["edit"]
      - receipt JSON
    """
    # derive duration from mel frames if present
    frames = int(src_meta.get("mel_frames", 0))
    duration_sec = timebase.mel_frame_to_sec(frames) if frames > 0 else 0.0

    # clamp region values if present
    region = None
    if req.start_sec is not None and req.end_sec is not None:
        a, b = clamp_region(
            start_sec=float(req.start_sec),
            end_sec=float(req.end_sec),
            duration_sec=float(duration_sec),
        )
        region = {"start_sec": float(a), "end_sec": float(b)}

    eid = make_edit_id(req, src_meta)

    fade_sec = 0.08
    if isinstance(req.extra, dict) and "fade_sec" in req.extra:
        fade_sec = float(max(0.0, _safe_float(req.extra.get("fade_sec"), fade_sec)))

    meta: Dict[str, Any] = {
        "edit_id": str(eid),
        "edit_type": str(req.edit_type).lower(),
        "attempt": int(req.attempt),
        "seed_delta": int(req.seed_delta),
        "strength": float(req.strength),
        "timebase": {
            "sample_rate": int(timebase.sample_rate),
            "hop_length": int(timebase.hop_length),
            "frames_per_sec": float(timebase.frames_per_sec()),
        },
        "fade_sec": float(fade_sec),
        "source": {
            "src_mel_pt": str(Path(req.src_mel_pt).resolve()),
            "src_wav": str(Path(req.src_wav).resolve()) if req.src_wav else "",
            "prompt_hash": _sha1_str(_safe_str(src_prompt)),
            "lyrics_hash": _sha1_str(_safe_str(src_lyrics)) if _safe_str(src_lyrics).strip() else "",
            "mel_frames": int(frames),
            "duration_sec": float(duration_sec),
        },
        "overrides": {
            "prompt_override": _safe_str(req.prompt_override) if (req.prompt_override and _safe_str(req.prompt_override).strip()) else "",
            "lyrics_override_present": bool(_safe_str(req.lyrics_override).strip()) if req.lyrics_override is not None else False,
        },
        "inference_overrides": {
            "steps_override": int(req.steps_override) if req.steps_override is not None else None,
            "guidance_override": float(req.guidance_override) if req.guidance_override is not None else None,
        },
        "params": {
            "region": region,
            "extend_sec": float(req.extend_sec) if req.extend_sec is not None else None,
        },
    }

    if isinstance(req.extra, dict):
        # keep a shallow copy, no huge blobs
        meta["extra"] = dict(req.extra)

    return meta


# ============================================================
# Edit planning / slicing / stitching
# ============================================================

def make_repaint_inputs(src_mel: torch.Tensor, req: BelelEditRequest, *, tb: BelelTimebase) -> Dict[str, Any]:
    """
    Returns:
      {
        "start_frame": int,
        "end_frame": int,
        "fade_frames": int,
        "left": [80,a],
        "mid":  [80,b-a],
        "right":[80,T-b],
      }
    """
    mel = _to_mel_2d(src_mel)
    T = int(mel.shape[1])

    # derive duration from mel length
    duration_sec = tb.mel_frame_to_sec(T)

    a_sec, b_sec = clamp_region(
        start_sec=float(req.start_sec or 0.0),
        end_sec=float(req.end_sec or 0.0),
        duration_sec=float(duration_sec),
    )

    a = int(max(0, min(T, tb.sec_to_mel_frame(a_sec))))
    b = int(max(0, min(T, tb.sec_to_mel_frame(b_sec))))
    if b < a:
        a, b = b, a
    if b == a:
        b = min(T, a + 1)

    fade_sec = 0.08
    if isinstance(req.extra, dict) and "fade_sec" in req.extra:
        fade_sec = float(max(0.0, _safe_float(req.extra.get("fade_sec"), fade_sec)))
    fade_frames = int(max(0, tb.sec_to_mel_frame(fade_sec)))

    # clamp fade to avoid eating the entire region
    region_len = int(b - a)
    fade_frames = min(fade_frames, max(0, region_len // 2), a, T - b)

    left = mel[:, :a]
    mid = mel[:, a:b]
    right = mel[:, b:]

    return {
        "start_sec": float(a_sec),
        "end_sec": float(b_sec),
        "start_frame": int(a),
        "end_frame": int(b),
        "fade_frames": int(fade_frames),
        "left": left,
        "mid": mid,
        "right": right,
        "duration_sec": float(duration_sec),
        "total_frames": int(T),
    }


def stitch_repaint(
    left: torch.Tensor,
    mid: torch.Tensor,
    right: torch.Tensor,
    *,
    fade_frames: int,
    strength: float = 1.0,
) -> torch.Tensor:
    """
    Stitch left + mid + right with cosine crossfades at the two boundaries.

    Boundary 1: end(left) <-> start(mid)
    Boundary 2: end(mid)  <-> start(right)

    fade_frames is clamped per-boundary to available lengths.
    """
    left = _to_mel_2d(left)
    mid = _to_mel_2d(mid)
    right = _to_mel_2d(right)

    fade = int(max(0, fade_frames))
    if fade == 0:
        return torch.cat([left, mid, right], dim=1)

    # boundary 1
    f1 = min(fade, int(left.shape[1]), int(mid.shape[1]))
    if f1 > 0:
        w = _cosine_fade(f1, device=left.device, dtype=left.dtype)  # [1,f1]
        l_keep = left[:, :-f1]
        l_tail = left[:, -f1:]
        m_head = mid[:, :f1]
        m_rest = mid[:, f1:]
        b1 = l_tail * (1.0 - w) + m_head * w
        left_mid = torch.cat([l_keep, b1, m_rest], dim=1)
    else:
        left_mid = torch.cat([left, mid], dim=1)

    # boundary 2
    f2 = min(fade, int(left_mid.shape[1]), int(right.shape[1]))
    # For boundary 2 we only fade the *end* of (left_mid) with start(right)
    if f2 > 0:
        w = _cosine_fade(f2, device=left_mid.device, dtype=left_mid.dtype)
        lm_keep = left_mid[:, :-f2]
        lm_tail = left_mid[:, -f2:]
        r_head = right[:, :f2]
        r_rest = right[:, f2:]
        b2 = lm_tail * (1.0 - w) + r_head * w
        out = torch.cat([lm_keep, b2, r_rest], dim=1)
    else:
        out = torch.cat([left_mid, right], dim=1)

    return out.float()


def extend_plan(src_mel: torch.Tensor, req: BelelEditRequest, *, tb: BelelTimebase) -> Dict[str, Any]:
    """
    Plan extension length and join fade.

    Returns:
      {
        "add_frames": int,
        "fade_frames": int,
        "extend_sec": float,
      }
    """
    mel = _to_mel_2d(src_mel)
    extend_sec = float(req.extend_sec or 0.0)
    add_frames = int(max(1, tb.sec_to_mel_frame(extend_sec)))

    fade_sec = 0.08
    if isinstance(req.extra, dict) and "fade_sec" in req.extra:
        fade_sec = float(max(0.0, _safe_float(req.extra.get("fade_sec"), fade_sec)))
    fade_frames = int(max(0, tb.sec_to_mel_frame(fade_sec)))
    fade_frames = min(fade_frames, int(mel.shape[1]), add_frames)

    return {
        "extend_sec": float(extend_sec),
        "add_frames": int(add_frames),
        "fade_frames": int(fade_frames),
    }


# ============================================================
# Filenames + receipts
# ============================================================

def default_edit_filename(*, src_name: str, edit_id: str, edit_type: str, ext: str = ".wav") -> str:
    """
    Deterministic, UI-friendly output name.
    """
    src_stem = Path(src_name).stem
    e = str(edit_id)[:12]
    t = str(edit_type).lower()
    if not ext.startswith("."):
        ext = "." + ext
    return f"{src_stem}__{t}__{e}{ext}"


def write_edit_receipt_json(path: Union[str, Path], payload: Dict[str, Any]) -> str:
    """
    Writes a receipt JSON. Returns the absolute path.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p.resolve())