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
    mel_path: str
    prompt: str
    lyrics: str

    # extra metadata (safe defaults)
    sidecar_path: str = ""
    wav_path: str = ""
    meta: Dict[str, Any] = None

    # distill tags (optional)
    steps: int = 0
    guidance: float = 0.0
    seed: Optional[int] = None
    utc: str = ""

    # caching (optional)
    cache_key: str = ""
    cond_cache_path: str = ""


# ----------------------------
# Utilities
# ----------------------------

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_mel_pt(path: Path) -> Tuple[torch.Tensor, Dict[str, Any]]:
    """
    Accepts:
      - {"mel": tensor, ...} OR tensor
    Returns:
      mel [80, T] float32
      payload dict (empty if tensor-only)
    """
    obj = torch.load(str(path), map_location="cpu")
    payload: Dict[str, Any] = obj if isinstance(obj, dict) else {}
    mel = obj["mel"] if isinstance(obj, dict) and "mel" in obj else obj

    if mel.ndim == 3 and mel.shape[0] == 1:
        mel = mel[0]
    if mel.ndim != 2 or mel.shape[0] != 80:
        raise ValueError(f"Bad mel shape in {path}: {tuple(mel.shape)}")
    return mel.float(), payload


def _extract_text_from_mel_payload(payload: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    """
    Reads optional fields from mel sidecar payload:
      {"mel": tensor, "prompt": str, "lyrics": str, "meta": {...}}
    """
    if not isinstance(payload, dict):
        return "", "", {}
    prompt = str(payload.get("prompt", "") or "")
    lyrics = str(payload.get("lyrics", "") or "")
    meta = payload.get("meta", {})
    meta = dict(meta) if isinstance(meta, dict) else {}
    return prompt, lyrics, meta


def _extract_text_and_tags_from_wav_sidecar(side: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    """
    Reads wav .json sidecar written by your generator.
    Expected keys (best-effort):
      prompt, lyrics, steps, guidance, seed, utc, extra
    """
    if not isinstance(side, dict):
        return "", "", {}
    prompt = str(side.get("prompt", "") or "")
    lyrics = str(side.get("lyrics", "") or "")
    return prompt, lyrics, side


def _merge_text(prompt_a: str, lyrics_a: str, prompt_b: str, lyrics_b: str) -> Tuple[str, str]:
    """
    Priority merge: use A if present, else B.
    """
    prompt = prompt_a if (prompt_a or "").strip() else (prompt_b or "")
    lyrics = lyrics_a if (lyrics_a or "").strip() else (lyrics_b or "")
    return prompt, lyrics


def _sidecar_steps_guidance_seed_utc(side: Dict[str, Any]) -> Tuple[int, float, Optional[int], str, Dict[str, Any]]:
    steps = 0
    guidance = 0.0
    seed: Optional[int] = None
    utc = ""
    extra: Dict[str, Any] = {}

    if isinstance(side, dict):
        if side.get("steps", None) is not None:
            try:
                steps = int(side["steps"])
            except Exception:
                pass
        if side.get("guidance", None) is not None:
            try:
                guidance = float(side["guidance"])
            except Exception:
                pass
        if side.get("seed", None) is not None:
            try:
                seed = int(side["seed"])
            except Exception:
                seed = None
        utc = str(side.get("utc", "") or "")
        ex = side.get("extra", {})
        extra = dict(ex) if isinstance(ex, dict) else {}

    return steps, guidance, seed, utc, extra


def _default_cache_key(prompt: str, lyrics: str) -> str:
    return _sha1((prompt or "") + "\n" + (lyrics or ""))


def collate_mels(
    batch: List[BelelMelItem],
    *,
    device: str = "cuda",
    pad_value: float = -4.0,
    max_len: Optional[int] = None,
    return_meta: bool = False,
) -> Union[
    Tuple[torch.Tensor, List[str], List[str]],
    Tuple[torch.Tensor, List[str], List[str], List[Dict[str, Any]]],
]:
    """
    Returns (default):
      mel: [B,80,Tmax] float32
      prompts: List[str]
      lyrics: List[str]

    If return_meta=True:
      returns (mel, prompts, lyrics, metas)
      metas[i] includes sidecar/meta/steps/guidance/seed/cache_key/cond_cache_path etc.
    """
    if not batch:
        raise ValueError("collate_mels received empty batch")

    mels: List[torch.Tensor] = []
    prompts: List[str] = []
    lyrics_list: List[str] = []
    metas: List[Dict[str, Any]] = []

    for it in batch:
        mel, payload = _load_mel_pt(Path(it.mel_path))
        if max_len is not None and mel.shape[-1] > int(max_len):
            mel = mel[:, : int(max_len)]
        mels.append(mel)

        prompts.append(str(it.prompt or ""))
        lyrics_list.append(str(it.lyrics or ""))

        if return_meta:
            metas.append({
                "mel_path": it.mel_path,
                "wav_path": it.wav_path,
                "sidecar_path": it.sidecar_path,
                "steps": int(it.steps),
                "guidance": float(it.guidance),
                "seed": it.seed,
                "utc": it.utc,
                "cache_key": it.cache_key,
                "cond_cache_path": it.cond_cache_path,
                "meta": dict(it.meta or {}),
                "mel_payload_keys": list(payload.keys()) if isinstance(payload, dict) else [],
            })

    Tmax = max(int(m.shape[-1]) for m in mels)
    if max_len is not None:
        Tmax = min(Tmax, int(max_len))

    out = torch.full((len(mels), 80, Tmax), float(pad_value), dtype=torch.float32)
    for i, m in enumerate(mels):
        t = min(int(m.shape[-1]), Tmax)
        out[i, :, :t] = m[:, :t]

    out = out.to(device)

    if return_meta:
        return out, prompts, lyrics_list, metas
    return out, prompts, lyrics_list


# ----------------------------
# Dataset
# ----------------------------

class BelelMelFolder:
    """
    Flexible mel dataset with metadata.

    Layouts supported:

    (A) Plain mel folder:
        mel_dir/*.pt
      Each .pt must be mel tensor or {"mel": tensor}
      No prompts/lyrics unless embedded in mel payload.

    (B) Engine output folder:
        out_dir/
          *.wav
          *.json        (wav sidecars with prompt/lyrics/steps/guidance/seed)
          mels/*.pt     (mel sidecars)
      This mode triggers automatically if out_dir/mels exists.

    Text priority order:
      1) mel payload prompt/lyrics if present
      2) wav sidecar prompt/lyrics
      3) ""

    Optional: compute cond_cache_path (air-gapped cached embedding file path).
    """

    def __init__(
        self,
        mel_dir: Union[str, Path],
        *,
        max_len: int = 2048,

        # filters
        require_sidecar: bool = False,
        require_prompt: bool = False,
        require_lyrics: bool = False,
        min_steps: Optional[int] = None,
        max_steps: Optional[int] = None,

        # embedding cache (optional)
        cond_cache_dir: Optional[Union[str, Path]] = None,
    ):
        self.root = Path(mel_dir)
        if not self.root.exists():
            raise FileNotFoundError(f"mel_dir not found: {self.root}")

        self.max_len = int(max_len)

        self.require_sidecar = bool(require_sidecar)
        self.require_prompt = bool(require_prompt)
        self.require_lyrics = bool(require_lyrics)
        self.min_steps = None if min_steps is None else int(min_steps)
        self.max_steps = None if max_steps is None else int(max_steps)

        self.cond_cache_dir = Path(cond_cache_dir) if cond_cache_dir else None
        if self.cond_cache_dir:
            self.cond_cache_dir.mkdir(parents=True, exist_ok=True)

        # Detect engine output layout
        self.mels_dir = self.root / "mels"
        self.is_engine_layout = self.mels_dir.exists() and self.mels_dir.is_dir()

        self.items: List[BelelMelItem] = []
        self._index()

    def _accept(self, item: BelelMelItem) -> bool:
        if self.require_sidecar and not item.sidecar_path:
            return False
        if self.require_prompt and not (item.prompt or "").strip():
            return False
        if self.require_lyrics and not (item.lyrics or "").strip():
            return False
        if self.min_steps is not None and int(item.steps) < int(self.min_steps):
            return False
        if self.max_steps is not None and int(item.steps) > int(self.max_steps):
            return False
        return True

    def _index(self) -> None:
        self.items.clear()

        if self.is_engine_layout:
            # Engine layout: out_dir/mels/*.pt and optional wav sidecars out_dir/*.json
            for mel_pt in sorted(self.mels_dir.glob("*.pt")):
                stem = mel_pt.name.replace(".pt", "")
                wav_path = self.root / f"{stem}.wav"
                wav_sidecar = self.root / f"{stem}.json"

                side = _read_json(wav_sidecar) if wav_sidecar.exists() else {}
                side_prompt, side_lyrics, side_full = _extract_text_and_tags_from_wav_sidecar(side)

                mel_tensor, mel_payload = _load_mel_pt(mel_pt)
                mel_prompt, mel_lyrics, mel_meta = _extract_text_from_mel_payload(mel_payload)

                # merge prompt/lyrics with mel payload priority
                prompt, lyrics = _merge_text(mel_prompt, mel_lyrics, side_prompt, side_lyrics)

                steps, guidance, seed, utc, extra = _sidecar_steps_guidance_seed_utc(side_full)

                cache_key = _default_cache_key(prompt, lyrics)
                cond_cache_path = ""
                if self.cond_cache_dir is not None:
                    cond_cache_path = str(self.cond_cache_dir / f"{cache_key}.pt")

                item = BelelMelItem(
                    mel_path=str(mel_pt),
                    prompt=prompt,
                    lyrics=lyrics,
                    sidecar_path=str(wav_sidecar) if wav_sidecar.exists() else "",
                    wav_path=str(wav_path) if wav_path.exists() else "",
                    meta={
                        "mel_meta": mel_meta,
                        "sidecar": side_full,
                        "extra": extra,
                    },
                    steps=steps,
                    guidance=guidance,
                    seed=seed,
                    utc=utc,
                    cache_key=cache_key,
                    cond_cache_path=cond_cache_path,
                )

                if self._accept(item):
                    self.items.append(item)

        else:
            # Plain mel dir: mel_dir/*.pt
            for mel_pt in sorted(self.root.glob("*.pt")):
                mel_tensor, payload = _load_mel_pt(mel_pt)
                mel_prompt, mel_lyrics, mel_meta = _extract_text_from_mel_payload(payload)

                prompt = mel_prompt
                lyrics = mel_lyrics

                cache_key = _default_cache_key(prompt, lyrics)
                cond_cache_path = ""
                if self.cond_cache_dir is not None:
                    cond_cache_path = str(self.cond_cache_dir / f"{cache_key}.pt")

                item = BelelMelItem(
                    mel_path=str(mel_pt),
                    prompt=prompt,
                    lyrics=lyrics,
                    sidecar_path="",
                    wav_path="",
                    meta={"mel_meta": mel_meta},
                    steps=0,
                    guidance=0.0,
                    seed=None,
                    utc="",
                    cache_key=cache_key,
                    cond_cache_path=cond_cache_path,
                )

                if self._accept(item):
                    self.items.append(item)

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[BelelMelItem]:
        for it in self.items:
            yield it
