from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Iterator
import json
import hashlib

import torch


# ----------------------------
# Data container
# ----------------------------

@dataclass
class BelelDistillItem:
    mel_path: str
    wav_path: str
    sidecar_path: str

    mel: torch.Tensor          # [80, T] float32 in [-4,4] (engine contract)
    prompt: str
    lyrics: str

    steps: int
    guidance: float
    seed: Optional[int]

    # provenance
    prompt_hash: str
    lyrics_hash: str
    utc: str
    extra: Dict[str, Any]      # ckpts, duration, any custom fields

    # optional embedding cache file (if present)
    emb_path: str              # may be "" if not cached yet


# ----------------------------
# Helpers
# ----------------------------

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_mel_pt(path: Path) -> torch.Tensor:
    """
    Accepts:
      {"mel": tensor, ...} or tensor
    Returns mel [80,T] float32
    """
    obj = torch.load(str(path), map_location="cpu")
    if isinstance(obj, dict) and "mel" in obj:
        mel = obj["mel"]
    else:
        mel = obj

    if mel.ndim == 3 and mel.shape[0] == 1:
        mel = mel[0]
    if mel.ndim != 2 or mel.shape[0] != 80:
        raise ValueError(f"Bad mel shape in {path}: {tuple(mel.shape)}")
    return mel.float()


def pad_mels(mels: List[torch.Tensor], pad_value: float = -4.0, max_len: Optional[int] = None) -> torch.Tensor:
    """
    Pads list of [80,T] -> [B,80,Tmax]
    """
    if not mels:
        raise ValueError("pad_mels received empty list")
    Tmax = max(int(m.shape[-1]) for m in mels)
    if max_len is not None:
        Tmax = min(Tmax, int(max_len))

    out = torch.full((len(mels), 80, Tmax), float(pad_value), dtype=torch.float32)
    for i, m in enumerate(mels):
        t = min(int(m.shape[-1]), Tmax)
        out[i, :, :t] = m[:, :t]
    return out


def default_embedding_cache_path(cache_dir: Path, prompt: str, lyrics: str) -> Path:
    """
    Stable cache key. Air-gapped safe.
    """
    key = _sha1((prompt or "") + "\n" + (lyrics or ""))
    return cache_dir / f"{key}.pt"


# ----------------------------
# Dataset
# ----------------------------

class BelelDistillFolder:
    """
    Reads distillation items from a Belel outputs directory.

    Expected layout:
      out_dir/
        *.wav
        *.json                (wav sidecars written by generator)
        mels/
          *.pt                (mel sidecars written by engine.save_mel)

    Optional embedding cache:
      emb_cache_dir/
        <sha1(prompt+lyrics)>.pt

    This keeps *all* the metadata you wanted, but stays as a pure dataset module.
    """

    def __init__(
        self,
        out_dir: str,
        *,
        max_len: int = 2048,
        require_sidecar: bool = True,
        require_mel: bool = True,
        emb_cache_dir: Optional[str] = None,
    ):
        self.root = Path(out_dir)
        if not self.root.exists():
            raise FileNotFoundError(f"out_dir not found: {self.root}")

        self.mels_dir = self.root / "mels"
        self.max_len = int(max_len)
        self.require_sidecar = bool(require_sidecar)
        self.require_mel = bool(require_mel)

        self.emb_cache_dir = Path(emb_cache_dir) if emb_cache_dir else None
        if self.emb_cache_dir:
            self.emb_cache_dir.mkdir(parents=True, exist_ok=True)

        self.wavs = sorted(self.root.glob("*.wav"))

    def __len__(self) -> int:
        return len(self.wavs)

    def __iter__(self) -> Iterator[BelelDistillItem]:
        for wav_path in self.wavs:
            sidecar = wav_path.with_suffix(".json")
            mel_pt = self.mels_dir / wav_path.name.replace(".wav", ".pt")

            if self.require_sidecar and not sidecar.exists():
                continue
            if self.require_mel and not mel_pt.exists():
                continue

            side = _read_json(sidecar) if sidecar.exists() else {}

            prompt = str(side.get("prompt", "") or "")
            lyrics = str(side.get("lyrics", "") or "")

            steps = int(side.get("steps", 0) or 0)
            guidance = float(side.get("guidance", 0.0) or 0.0)
            seed = side.get("seed", None)
            seed = None if seed is None else int(seed)

            prompt_hash = str(side.get("prompt_hash", "") or _sha1(prompt))
            lyrics_hash = str(side.get("lyrics_hash", "") or (_sha1(lyrics) if lyrics else ""))

            utc = str(side.get("utc", "") or "")
            extra = side.get("extra", {})
            extra = dict(extra) if isinstance(extra, dict) else {}

            mel = load_mel_pt(mel_pt) if mel_pt.exists() else torch.zeros((80, 1), dtype=torch.float32)
            if mel.shape[-1] > self.max_len:
                mel = mel[:, : self.max_len]

            emb_path = ""
            if self.emb_cache_dir is not None:
                ep = default_embedding_cache_path(self.emb_cache_dir, prompt, lyrics)
                emb_path = str(ep)

            yield BelelDistillItem(
                mel_path=str(mel_pt),
                wav_path=str(wav_path),
                sidecar_path=str(sidecar),
                mel=mel,
                prompt=prompt,
                lyrics=lyrics,
                steps=steps,
                guidance=guidance,
                seed=seed,
                prompt_hash=prompt_hash,
                lyrics_hash=lyrics_hash,
                utc=utc,
                extra=extra,
                emb_path=emb_path,
            )
