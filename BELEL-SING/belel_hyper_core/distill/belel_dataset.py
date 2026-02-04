from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Iterable, Tuple
import json
import torch
import numpy as np


def _load_sidecar_json(path: Path) -> Dict[str, str]:
    js = path.with_suffix(".json")
    if not js.exists():
        return {"prompt": "", "lyrics": ""}
    try:
        obj = json.loads(js.read_text(encoding="utf-8"))
        return {
            "prompt": str(obj.get("prompt", "") or ""),
            "lyrics": str(obj.get("lyrics", "") or ""),
        }
    except Exception:
        return {"prompt": "", "lyrics": ""}


class BelelMelFolder:
    """
    Iterates mel files and returns dict items:
      {
        "mel":   Tensor[80, T],
        "prompt": str,
        "lyrics": str
      }

    Formats:
      - .pt: dict {"mel": tensor, "prompt": str?, "lyrics": str?} OR raw mel tensor
      - .npy/.npz: mel only; prompt/lyrics from sidecar .json
    """

    def __init__(self, root: str, max_len: int = 2048):
        self.root = Path(root)
        self.max_len = int(max_len)
        if not self.root.exists():
            raise FileNotFoundError(f"Mel directory not found: {self.root}")

        self.files = sorted([p for p in self.root.rglob("*") if p.suffix in (".pt", ".npy", ".npz")])
        if not self.files:
            raise RuntimeError(f"No mel files found in {self.root}")

    def __len__(self) -> int:
        return len(self.files)

    def __iter__(self) -> Iterable[Dict[str, Any]]:
        for p in self.files:
            item = self._load_item(p)
            yield item

    def _sanitize_mel(self, mel: torch.Tensor) -> torch.Tensor:
        if mel.ndim == 3 and mel.shape[0] == 1:
            mel = mel[0]
        if mel.ndim != 2:
            raise ValueError(f"Invalid mel dims {tuple(mel.shape)}, expected [80, T]")
        if mel.shape[0] != 80:
            raise ValueError(f"Expected 80 mel bins, got {mel.shape[0]}")
        if mel.shape[1] > self.max_len:
            mel = mel[:, : self.max_len]
        return mel.float()

    def _load_item(self, path: Path) -> Dict[str, Any]:
        prompt = ""
        lyrics = ""

        if path.suffix == ".pt":
            obj = torch.load(path, map_location="cpu")
            if isinstance(obj, dict) and "mel" in obj:
                mel = obj["mel"]
                prompt = str(obj.get("prompt", "") or "")
                lyrics = str(obj.get("lyrics", "") or "")
            else:
                mel = obj
                meta = _load_sidecar_json(path)
                prompt, lyrics = meta["prompt"], meta["lyrics"]

        elif path.suffix == ".npy":
            mel = torch.from_numpy(np.load(path))
            meta = _load_sidecar_json(path)
            prompt, lyrics = meta["prompt"], meta["lyrics"]

        elif path.suffix == ".npz":
            data = np.load(path)
            if "mel" not in data:
                raise KeyError(f"No 'mel' key in {path}")
            mel = torch.from_numpy(data["mel"])
            meta = _load_sidecar_json(path)
            prompt, lyrics = meta["prompt"], meta["lyrics"]

        else:
            raise ValueError(f"Unsupported file type: {path}")

        mel = self._sanitize_mel(mel)
        return {"mel": mel, "prompt": prompt, "lyrics": lyrics, "path": str(path)}


def collate_mels(
    batch: List[Dict[str, Any]],
    device: str = "cuda",
    pad_value: float = -4.0,
) -> Tuple[torch.Tensor, List[str], List[str]]:
    """
    Returns:
      mel:    [B, 80, T_max]
      prompts: list[str]
      lyrics:  list[str]
    """
    mels = [b["mel"] for b in batch]
    prompts = [str(b.get("prompt", "") or "") for b in batch]
    lyrics = [str(b.get("lyrics", "") or "") for b in batch]

    max_len = max(m.shape[1] for m in mels)
    out = torch.full((len(mels), 80, max_len), float(pad_value), dtype=torch.float32)
    for i, m in enumerate(mels):
        out[i, :, : m.shape[1]] = m

    return out.to(device), prompts, lyrics
