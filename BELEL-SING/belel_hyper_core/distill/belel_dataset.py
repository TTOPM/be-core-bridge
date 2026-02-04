from pathlib import Path
import torch
import numpy as np
from typing import List, Tuple, Iterable


class BelelMelFolder:
    """
    Iterable dataset over a folder of mel tensors.

    Supported formats:
      - .pt   (dict with key 'mel' or raw tensor)
      - .npy  (numpy array)
      - .npz  (expects key 'mel')

    Output shape: [80, T]
    """

    def __init__(self, root: str, max_len: int = 2048):
        self.root = Path(root)
        self.max_len = max_len

        if not self.root.exists():
            raise FileNotFoundError(f"Mel directory not found: {self.root}")

        self.files = sorted(
            [p for p in self.root.rglob("*") if p.suffix in (".pt", ".npy", ".npz")]
        )

        if not self.files:
            raise RuntimeError(f"No mel files found in {self.root}")

    def __len__(self) -> int:
        return len(self.files)

    def __iter__(self) -> Iterable[torch.Tensor]:
        for p in self.files:
            mel = self._load(p)
            mel = self._sanitize(mel)
            yield mel

    def _load(self, path: Path) -> torch.Tensor:
        if path.suffix == ".pt":
            obj = torch.load(path, map_location="cpu")
            if isinstance(obj, dict) and "mel" in obj:
                mel = obj["mel"]
            else:
                mel = obj

        elif path.suffix == ".npy":
            mel = torch.from_numpy(np.load(path))

        elif path.suffix == ".npz":
            data = np.load(path)
            if "mel" not in data:
                raise KeyError(f"No 'mel' key in {path}")
            mel = torch.from_numpy(data["mel"])

        else:
            raise ValueError(f"Unsupported file type: {path}")

        mel = mel.float()
        return mel

    def _sanitize(self, mel: torch.Tensor) -> torch.Tensor:
        """
        Ensure mel shape is [80, T] and trim/pad time dimension.
        """
        if mel.ndim == 3 and mel.shape[0] == 1:
            mel = mel[0]

        if mel.ndim != 2:
            raise ValueError(f"Invalid mel dims {mel.shape}, expected [80, T]")

        if mel.shape[0] != 80:
            raise ValueError(f"Expected 80 mel bins, got {mel.shape[0]}")

        # trim time
        if mel.shape[1] > self.max_len:
            mel = mel[:, : self.max_len]

        return mel


def collate_mels(
    batch: List[torch.Tensor],
    device: str = "cuda",
    pad_value: float = -4.0,
) -> torch.Tensor:
    """
    Collate list of [80, T] tensors into [B, 80, T_max]
    """
    max_len = max(m.shape[1] for m in batch)
    B = len(batch)

    out = torch.full((B, 80, max_len), pad_value, dtype=torch.float32)

    for i, mel in enumerate(batch):
        out[i, :, : mel.shape[1]] = mel

    return out.to(device)
