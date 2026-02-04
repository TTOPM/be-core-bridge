from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Iterator, Optional, Dict, Any, Union
import json
import hashlib

import torch


# ----------------------------
# Item
# ----------------------------

@dataclass
class BelelMelItem:
    """
    One training sample.

    mel_path: path to .pt containing mel tensor or dict containing {"mel": tensor, ...}
    prompt/lyrics: text conditioning fields
    meta: merged metadata dict (mel.meta overlays wav.json)
    item_id: deterministic id used for caching / dedupe / reproducibility
    """
    mel_path: str
    prompt: str
    lyrics: str
    meta: Dict[str, Any]
    item_id: str


# ----------------------------
# Utilities
# ----------------------------

def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_str(x: Any) -> str:
    try:
        return str(x or "")
    except Exception:
        return ""


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _load_mel_obj(path: Path) -> Any:
    """
    Loads the raw .pt object from disk.
    May be:
      - tensor
      - {"mel": tensor, "prompt": str, "lyrics": str, "meta": {...}, ...}
    """
    return torch.load(str(path), map_location="cpu")


def _extract_mel_tensor(obj: Any, path: Path, *, expected_bins: int = 80) -> torch.Tensor:
    """
    Returns mel [expected_bins, T] float32.

    Accepts:
      - tensor
      - {"mel": tensor, ...}
    """
    mel = obj["mel"] if isinstance(obj, dict) and "mel" in obj else obj

    if not isinstance(mel, torch.Tensor):
        raise ValueError(f"Mel payload is not a torch.Tensor in {path}")

    # Normalize shapes: [1,B,T] -> [B,T]
    if mel.ndim == 3 and mel.shape[0] == 1:
        mel = mel[0]

    if mel.ndim != 2 or int(mel.shape[0]) != int(expected_bins):
        raise ValueError(f"Bad mel shape in {path}: {tuple(mel.shape)} (expected [{expected_bins}, T])")

    return mel.float()


def _extract_text_meta_from_mel_pt(obj: Any) -> Tuple[str, str, Dict[str, Any]]:
    """
    Preferred source-of-truth for prompt/lyrics/meta is mel .pt itself.

    Expected:
      {"mel": tensor, "prompt": str, "lyrics": str, "meta": {...}}
    """
    if not isinstance(obj, dict):
        return "", "", {}

    prompt = _safe_str(obj.get("prompt", ""))
    lyrics = _safe_str(obj.get("lyrics", ""))
    meta = obj.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}

    return prompt, lyrics, meta


def _merge_meta(wav_meta: Dict[str, Any], mel_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge meta dictionaries; mel meta wins on collisions (mel artifact is the truth for distillation).
    """
    out: Dict[str, Any] = {}
    if isinstance(wav_meta, dict):
        out.update(wav_meta)
    if isinstance(mel_meta, dict):
        out.update(mel_meta)
    return out


def _resolve_field_priority(primary: str, fallback: str) -> str:
    """
    Field-by-field priority:
      - if primary is non-empty => use it
      - else fallback
    """
    return primary if (primary or "").strip() else fallback


def _make_item_id(mel_path: str, prompt: str, lyrics: str) -> str:
    """
    Stable id for caching and reproducibility.
    Includes mel_path + prompt+lyrics hashes so changes invalidate caches.
    """
    p = str(Path(mel_path).resolve())
    return _sha1(p + "::" + _sha1(prompt or "") + "::" + _sha1(lyrics or ""))


# ----------------------------
# Collation
# ----------------------------

def collate_mels(
    batch: List[BelelMelItem],
    *,
    device: str = "cuda",
    pad_value: float = -4.0,
    max_len: Optional[int] = None,
    expected_bins: int = 80,
    return_meta: bool = True,
) -> Tuple[torch.Tensor, List[str], List[str], List[Dict[str, Any]], List[str]]:
    """
    Returns:
      mel: [B,expected_bins,Tmax] float32
      prompts: List[str]
      lyrics: List[str]
      metas: List[Dict[str, Any]]   (empty dicts if return_meta=False)
      ids: List[str]

    Distillers can ignore metas/ids if they want, but they’re essential for:
      - cached conditioner embeddings keyed by id
      - provenance enforcement
      - per-item schedules/weights
    """
    if not batch:
        raise ValueError("collate_mels received empty batch")

    mels: List[torch.Tensor] = []
    prompts: List[str] = []
    lyrics_list: List[str] = []
    metas: List[Dict[str, Any]] = []
    ids: List[str] = []

    Tmax = 0

    for it in batch:
        p = Path(it.mel_path)
        obj = _load_mel_obj(p)
        mel = _extract_mel_tensor(obj, p, expected_bins=expected_bins)

        if max_len is not None and mel.shape[-1] > int(max_len):
            mel = mel[:, : int(max_len)]

        Tmax = max(Tmax, int(mel.shape[-1]))

        mels.append(mel)
        prompts.append(_safe_str(it.prompt))
        lyrics_list.append(_safe_str(it.lyrics))
        metas.append(dict(it.meta) if return_meta else {})
        ids.append(_safe_str(it.item_id))

    if max_len is not None:
        Tmax = min(Tmax, int(max_len))

    out = torch.full((len(mels), expected_bins, Tmax), float(pad_value), dtype=torch.float32)
    for i, m in enumerate(mels):
        t = min(int(m.shape[-1]), Tmax)
        out[i, :, :t] = m[:, :t]

    return out.to(device), prompts, lyrics_list, metas, ids


# ----------------------------
# Dataset
# ----------------------------

class BelelMelFolder:
    """
    Distillation-ready dataset with metadata priority and layout autodetection.

    Layouts supported:

    (1) Engine outputs:
        root/
          mels/*.pt
          *.json            (wav sidecars containing prompt/lyrics/steps/guidance/seed/ckpts/etc)

    (2) Plain mel folder:
        root/*.pt

    (3) Manifest mode (highest control):
        root/manifest.jsonl  (or a provided manifest path)
        Each line:
          {"mel_path": "...", "prompt": "...", "lyrics": "...", "meta": {...}}
    """

    def __init__(
        self,
        mel_dir: Union[str, Path],
        *,
        max_len: int = 2048,
        expected_bins: int = 80,
        require_text: bool = False,
        strict: bool = False,
        manifest: Optional[Union[str, Path]] = None,
        limit: Optional[int] = None,
    ):
        """
        require_text:
          - if True, drop samples where both prompt and lyrics are empty (after priority resolution)

        strict:
          - if True, any corrupted mel file raises immediately
          - if False, corrupted items are skipped

        manifest:
          - if provided and exists, manifest mode is used

        limit:
          - optional maximum number of items to index (useful for quick tests)
        """
        self.root = Path(mel_dir)
        if not self.root.exists():
            raise FileNotFoundError(f"mel_dir not found: {self.root}")

        self.max_len = int(max_len)
        self.expected_bins = int(expected_bins)
        self.require_text = bool(require_text)
        self.strict = bool(strict)
        self.limit = None if limit is None else int(limit)

        self.manifest_path: Optional[Path] = None
        if manifest is not None:
            mp = Path(manifest)
            if mp.exists():
                self.manifest_path = mp
        else:
            # auto-detect manifest.jsonl in root
            mp = self.root / "manifest.jsonl"
            if mp.exists():
                self.manifest_path = mp

        # Detect engine layout
        self.mels_dir = self.root / "mels"
        self.is_engine_layout = self.mels_dir.exists() and self.mels_dir.is_dir()

        self.items: List[BelelMelItem] = []
        self._index()

    def _index(self) -> None:
        self.items.clear()

        if self.manifest_path is not None:
            self._index_manifest_mode(self.manifest_path)
        elif self.is_engine_layout:
            self._index_engine_layout()
        else:
            self._index_plain_layout()

        # deterministic ordering (important for reproducibility)
        self.items.sort(key=lambda it: it.item_id)

        if self.limit is not None:
            self.items = self.items[: self.limit]

    def _index_manifest_mode(self, manifest_path: Path) -> None:
        """
        Highest control indexing: explicit rows.
        """
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                if self.strict:
                    raise
                continue

            mel_path = _safe_str(obj.get("mel_path", ""))
            if not mel_path:
                continue

            mel_p = Path(mel_path)
            if not mel_p.is_absolute():
                mel_p = (manifest_path.parent / mel_p).resolve()

            prompt = _safe_str(obj.get("prompt", ""))
            lyrics = _safe_str(obj.get("lyrics", ""))
            meta = obj.get("meta", {})
            if not isinstance(meta, dict):
                meta = {}

            if self.require_text and not (prompt or lyrics):
                continue

            # integrity check (optional)
            if not mel_p.exists():
                if self.strict:
                    raise FileNotFoundError(f"Missing mel_path in manifest: {mel_p}")
                continue

            # optional mel sanity check
            try:
                _ = _extract_mel_tensor(_load_mel_obj(mel_p), mel_p, expected_bins=self.expected_bins)
            except Exception:
                if self.strict:
                    raise
                continue

            item_id = _make_item_id(str(mel_p), prompt, lyrics)
            self.items.append(
                BelelMelItem(
                    mel_path=str(mel_p),
                    prompt=prompt,
                    lyrics=lyrics,
                    meta=meta,
                    item_id=item_id,
                )
            )

    def _index_plain_layout(self) -> None:
        for mel_pt in sorted(self.root.glob("*.pt")):
            try:
                obj = _load_mel_obj(mel_pt)
                prompt_m, lyrics_m, meta_m = _extract_text_meta_from_mel_pt(obj)

                # sanity check mel shape
                _ = _extract_mel_tensor(obj, mel_pt, expected_bins=self.expected_bins)

                prompt = _safe_str(prompt_m)
                lyrics = _safe_str(lyrics_m)
                meta = dict(meta_m) if isinstance(meta_m, dict) else {}
            except Exception:
                if self.strict:
                    raise
                continue

            if self.require_text and not (prompt or lyrics):
                continue

            item_id = _make_item_id(str(mel_pt), prompt, lyrics)
            self.items.append(
                BelelMelItem(
                    mel_path=str(mel_pt),
                    prompt=prompt,
                    lyrics=lyrics,
                    meta=meta,
                    item_id=item_id,
                )
            )

    def _index_engine_layout(self) -> None:
        """
        Engine layout: root/mels/*.pt and optional wav sidecars root/*.json

        Priority is per-field:
          prompt: mel_pt.prompt -> wav_json.prompt -> ""
          lyrics: mel_pt.lyrics -> wav_json.lyrics -> ""
          meta: merged (wav_meta then mel_meta overlays)
        """
        for mel_pt in sorted(self.mels_dir.glob("*.pt")):
            stem = mel_pt.stem
            wav_sidecar = self.root / f"{stem}.json"

            # 1) mel pt fields (highest priority)
            mel_prompt, mel_lyrics, mel_meta = "", "", {}
            obj = None
            try:
                obj = _load_mel_obj(mel_pt)
                mel_prompt, mel_lyrics, mel_meta = _extract_text_meta_from_mel_pt(obj)
                # sanity check mel shape
                _ = _extract_mel_tensor(obj, mel_pt, expected_bins=self.expected_bins)
            except Exception:
                if self.strict:
                    raise
                continue

            # 2) wav sidecar fallback
            wav_meta = _safe_read_json(wav_sidecar) if wav_sidecar.exists() else {}
            wav_prompt = _safe_str(wav_meta.get("prompt", ""))
            wav_lyrics = _safe_str(wav_meta.get("lyrics", ""))

            prompt = _resolve_field_priority(_safe_str(mel_prompt), wav_prompt)
            lyrics = _resolve_field_priority(_safe_str(mel_lyrics), wav_lyrics)

            meta = _merge_meta(wav_meta if isinstance(wav_meta, dict) else {}, mel_meta if isinstance(mel_meta, dict) else {})

            if self.require_text and not (prompt or lyrics):
                continue

            item_id = _make_item_id(str(mel_pt), prompt, lyrics)
            self.items.append(
                BelelMelItem(
                    mel_path=str(mel_pt),
                    prompt=prompt,
                    lyrics=lyrics,
                    meta=meta,
                    item_id=item_id,
                )
            )

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[BelelMelItem]:
        for it in self.items:
            yield it

    def as_list(self) -> List[BelelMelItem]:
        return list(self.items)

    def summary(self) -> Dict[str, Any]:
        """
        Lightweight inspection for sanity checks.
        """
        n = len(self.items)
        with_text = sum(1 for it in self.items if (it.prompt or it.lyrics))
        return {
            "root": str(self.root),
            "count": n,
            "with_text": int(with_text),
            "engine_layout": bool(self.is_engine_layout),
            "manifest": str(self.manifest_path) if self.manifest_path else "",
            "expected_bins": int(self.expected_bins),
            "max_len": int(self.max_len),
            "require_text": bool(self.require_text),
            "strict": bool(self.strict),
        }
