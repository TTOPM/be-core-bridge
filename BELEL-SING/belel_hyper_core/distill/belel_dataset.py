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

    integrity:
      - "ok": passed indexing rules
      - "missing_text": dropped due to require_text/strict_provenance
      - "missing_file": referenced mel does not exist
      - "bad_mel": malformed mel tensor / wrong shape
      - "bad_manifest": manifest row invalid
      - "bad_json": sidecar json unreadable
    """
    mel_path: str
    prompt: str
    lyrics: str
    meta: Dict[str, Any]
    item_id: str
    integrity: str = "ok"
    mel_frames: Optional[int] = None


# ----------------------------
# Utilities
# ----------------------------

def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _safe_str(x: Any) -> str:
    try:
        return str(x or "")
    except Exception:
        return ""


def _sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def _load_pt(path: Path) -> Any:
    return torch.load(str(path), map_location="cpu")


def _extract_mel_tensor(obj: Any, path: Path, *, expected_bins: int = 80) -> torch.Tensor:
    """
    Returns mel [expected_bins, T] float32.

    Accepts:
      - tensor
      - {"mel": tensor, ...}

    Normalizes shapes:
      [1, expected_bins, T] -> [expected_bins, T]
    """
    mel = obj["mel"] if isinstance(obj, dict) and "mel" in obj else obj

    if not isinstance(mel, torch.Tensor):
        raise ValueError(f"Mel payload is not a torch.Tensor in {path}")

    if mel.ndim == 3 and mel.shape[0] == 1:
        mel = mel[0]

    if mel.ndim != 2 or int(mel.shape[0]) != int(expected_bins):
        raise ValueError(f"Bad mel shape in {path}: {tuple(mel.shape)} (expected [{expected_bins}, T])")

    return mel.float()


def _extract_text_meta_from_mel_pt(obj: Any) -> Tuple[str, str, Dict[str, Any]]:
    """
    Highest priority provenance source: mel .pt dict fields.

    Best case:
      {"mel": tensor, "prompt": str, "lyrics": str, "meta": {...}}

    Returns:
      prompt, lyrics, meta_dict
    """
    if not isinstance(obj, dict):
        return "", "", {}

    prompt = _safe_str(obj.get("prompt", ""))
    lyrics = _safe_str(obj.get("lyrics", ""))
    meta = obj.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}

    return prompt, lyrics, meta


def _resolve_field_priority(primary: str, fallback: str) -> str:
    """
    Field-by-field priority:
      - if primary is non-empty => use it
      - else fallback
    """
    p = (primary or "").strip()
    return primary if p else fallback


def _merge_meta(wav_meta: Dict[str, Any], mel_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge meta dictionaries; mel meta wins on collisions.
    """
    out: Dict[str, Any] = {}
    if isinstance(wav_meta, dict):
        out.update(wav_meta)
    if isinstance(mel_meta, dict):
        out.update(mel_meta)
    return out


def _normalize_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize known Belel provenance fields while preserving everything else.

    This does NOT delete unknown keys.
    It simply ensures canonical keys exist if equivalent aliases exist.
    """
    if not isinstance(meta, dict):
        return {}

    out = dict(meta)

    def _get(*keys):
        for k in keys:
            if k in out:
                return out[k]
        return None

    canonical = {
        "steps": _get("steps", "num_steps"),
        "guidance": _get("guidance", "cfg", "scale"),
        "seed": _get("seed"),
        "codec_ckpt": _get("codec_ckpt", "codec_checkpoint"),
        "denoiser_ckpt": _get("denoiser_ckpt", "denoiser_checkpoint"),
        "duration": _get("duration", "duration_sec"),
        "utc": _get("utc", "timestamp", "time_utc"),
    }

    for k, v in canonical.items():
        if v is not None:
            out[k] = v

    return out


def _make_item_id(mel_path: Union[str, Path], prompt: str, lyrics: str) -> str:
    """
    Stable id for caching and reproducibility.

    Includes:
      - absolute mel path (so duplicates in different dirs are distinct)
      - prompt hash
      - lyrics hash

    Any change to text invalidates caches automatically.
    """
    p = str(Path(mel_path).resolve())
    return _sha1(p + "::" + _sha1(prompt or "") + "::" + _sha1(lyrics or ""))


def _is_nonempty_text(prompt: str, lyrics: str, *, allow_empty_lyrics: bool) -> bool:
    has_prompt = bool((prompt or "").strip())
    has_lyrics = bool((lyrics or "").strip())
    if allow_empty_lyrics:
        return has_prompt or has_lyrics
    # require lyrics present if prompt-only is not allowed
    return has_prompt and has_lyrics


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
    return_ids: bool = True,
    return_lengths: bool = True,
) -> Tuple[
    torch.Tensor,
    List[str],
    List[str],
    List[Dict[str, Any]],
    List[str],
    List[int],
]:
    """
    Loads each mel .pt from disk and pads/truncates to batch Tmax.

    Returns (always as a 6-tuple for simplicity and stability):
      mel:      [B, expected_bins, Tmax] float32
      prompts:  List[str]
      lyrics:   List[str]
      metas:    List[Dict[str,Any]] (empty dicts if return_meta=False)
      ids:      List[str]           (empty strings if return_ids=False)
      lengths:  List[int]           (0s if return_lengths=False)

    Notes:
      - pads with pad_value (default -4.0, consistent with mel log-space conventions)
      - if max_len is set, truncates each sample to max_len and Tmax capped to max_len
    """
    if not batch:
        raise ValueError("collate_mels received empty batch")

    mels: List[torch.Tensor] = []
    prompts: List[str] = []
    lyrics_list: List[str] = []
    metas: List[Dict[str, Any]] = []
    ids: List[str] = []
    lengths: List[int] = []

    Tmax = 0

    for it in batch:
        p = Path(it.mel_path)
        obj = _load_pt(p)
        mel = _extract_mel_tensor(obj, p, expected_bins=expected_bins)

        if max_len is not None and mel.shape[-1] > int(max_len):
            mel = mel[:, : int(max_len)]

        tlen = int(mel.shape[-1])
        Tmax = max(Tmax, tlen)

        mels.append(mel)
        prompts.append(_safe_str(it.prompt))
        lyrics_list.append(_safe_str(it.lyrics))
        metas.append(dict(it.meta) if (return_meta and isinstance(it.meta, dict)) else {})
        ids.append(_safe_str(it.item_id) if return_ids else "")
        lengths.append(tlen if return_lengths else 0)

    if max_len is not None:
        Tmax = min(Tmax, int(max_len))

    out = torch.full((len(mels), expected_bins, Tmax), float(pad_value), dtype=torch.float32)
    for i, m in enumerate(mels):
        t = min(int(m.shape[-1]), Tmax)
        out[i, :, :t] = m[:, :t]

    return out.to(device), prompts, lyrics_list, metas, ids, lengths


# ----------------------------
# Dataset
# ----------------------------

class BelelMelFolder:
    """
    Distillation-ready dataset with metadata priority, layout autodetection, and reproducibility guards.

    Layouts supported:

    (1) Engine outputs:
        root/
          mels/*.pt
          *.json            (wav sidecars containing prompt/lyrics/steps/guidance/seed/ckpts/etc)

      Priority (field-level):
        prompt: mel_pt.prompt -> wav_json.prompt -> ""
        lyrics: mel_pt.lyrics -> wav_json.lyrics -> ""
        meta:   wav_meta base overlaid by mel_meta (mel wins)
        meta is normalized to canonical Belel keys while preserving extras.

    (2) Plain mel folder:
        root/*.pt
      prompt/lyrics/meta extracted from dict form if present, else empty.

    (3) Manifest mode (highest control):
        manifest.jsonl (auto-detected in root) OR explicit manifest path
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
        validate_mels: bool = True,
        strict_provenance: bool = False,
        allow_empty_lyrics: bool = True,
    ):
        """
        require_text:
          If True, drop samples where both prompt and lyrics are empty (after priority resolution).

        strict:
          If True, corrupted files/rows raise immediately.
          If False, corrupted items are skipped and counted.

        manifest:
          If provided and exists, manifest mode is used.
          Else auto-detect root/manifest.jsonl.

        limit:
          Optional maximum number of items to index (useful for quick tests).

        validate_mels:
          If True, verify mel tensors during indexing (shape check) and record mel_frames.
          If False, skip validation at index time (faster for huge datasets).

        strict_provenance:
          Engine layout requires prompt present (after priority resolution).
          Skips items without prompt.

        allow_empty_lyrics:
          If False and require_text is True, requires lyrics != "" too.
        """
        self.root = Path(mel_dir)
        if not self.root.exists():
            raise FileNotFoundError(f"mel_dir not found: {self.root}")

        self.max_len = int(max_len)
        self.expected_bins = int(expected_bins)
        self.require_text = bool(require_text)
        self.strict = bool(strict)
        self.limit = None if limit is None else int(limit)
        self.validate_mels = bool(validate_mels)
        self.strict_provenance = bool(strict_provenance)
        self.allow_empty_lyrics = bool(allow_empty_lyrics)

        # Diagnostics counters
        self.stats: Dict[str, int] = {
            "indexed": 0,
            "accepted": 0,
            "skipped": 0,
            "missing_file": 0,
            "bad_mel": 0,
            "missing_text": 0,
            "bad_manifest": 0,
        }

        # Manifest detection
        self.manifest_path: Optional[Path] = None
        if manifest is not None:
            mp = Path(manifest)
            if mp.exists():
                self.manifest_path = mp
        else:
            mp = self.root / "manifest.jsonl"
            if mp.exists():
                self.manifest_path = mp

        # Engine layout detection
        self.mels_dir = self.root / "mels"
        self.is_engine_layout = self.mels_dir.exists() and self.mels_dir.is_dir()

        self.items: List[BelelMelItem] = []
        self._index()

    def _accept_text_rules(self, prompt: str, lyrics: str) -> bool:
        prompt_s = (prompt or "").strip()
        lyrics_s = (lyrics or "").strip()

        if self.strict_provenance:
            # must have prompt
            if not prompt_s:
                return False

        if self.require_text:
            if not _is_nonempty_text(prompt_s, lyrics_s, allow_empty_lyrics=self.allow_empty_lyrics):
                return False

        return True

    def _index(self) -> None:
        self.items.clear()
        for k in self.stats:
            self.stats[k] = 0

        if self.manifest_path is not None:
            self._index_manifest_mode(self.manifest_path)
        elif self.is_engine_layout:
            self._index_engine_layout()
        else:
            self._index_plain_layout()

        # Deterministic ordering for reproducibility
        self.items.sort(key=lambda it: it.item_id)

        # Optional cap
        if self.limit is not None:
            self.items = self.items[: self.limit]

        self.stats["accepted"] = len(self.items)

    def _index_manifest_mode(self, manifest_path: Path) -> None:
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if not line.strip():
                continue

            self.stats["indexed"] += 1

            try:
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    raise ValueError("manifest row is not a dict")
            except Exception:
                self.stats["bad_manifest"] += 1
                self.stats["skipped"] += 1
                if self.strict:
                    raise
                continue

            mel_path_raw = _safe_str(obj.get("mel_path", ""))
            if not mel_path_raw:
                self.stats["bad_manifest"] += 1
                self.stats["skipped"] += 1
                if self.strict:
                    raise ValueError("manifest row missing mel_path")
                continue

            mel_p = Path(mel_path_raw)
            if not mel_p.is_absolute():
                mel_p = (manifest_path.parent / mel_p).resolve()

            if not mel_p.exists():
                self.stats["missing_file"] += 1
                self.stats["skipped"] += 1
                if self.strict:
                    raise FileNotFoundError(f"Missing mel_path in manifest: {mel_p}")
                continue

            prompt = _safe_str(obj.get("prompt", ""))
            lyrics = _safe_str(obj.get("lyrics", ""))
            meta = obj.get("meta", {})
            if not isinstance(meta, dict):
                meta = {}

            meta = _normalize_meta(meta)

            if not self._accept_text_rules(prompt, lyrics):
                self.stats["missing_text"] += 1
                self.stats["skipped"] += 1
                continue

            mel_frames: Optional[int] = None
            if self.validate_mels:
                try:
                    pt = _load_pt(mel_p)
                    mel = _extract_mel_tensor(pt, mel_p, expected_bins=self.expected_bins)
                    mel_frames = int(mel.shape[-1])
                except Exception:
                    self.stats["bad_mel"] += 1
                    self.stats["skipped"] += 1
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
                    integrity="ok",
                    mel_frames=mel_frames,
                )
            )

    def _index_plain_layout(self) -> None:
        for mel_pt in sorted(self.root.glob("*.pt")):
            self.stats["indexed"] += 1

            if not mel_pt.exists():
                self.stats["missing_file"] += 1
                self.stats["skipped"] += 1
                if self.strict:
                    raise FileNotFoundError(f"Missing mel file: {mel_pt}")
                continue

            try:
                obj = _load_pt(mel_pt)
                prompt_m, lyrics_m, meta_m = _extract_text_meta_from_mel_pt(obj)
                meta = meta_m if isinstance(meta_m, dict) else {}
                meta = _normalize_meta(meta)

                mel_frames: Optional[int] = None
                if self.validate_mels:
                    mel = _extract_mel_tensor(obj, mel_pt, expected_bins=self.expected_bins)
                    mel_frames = int(mel.shape[-1])

                prompt = _safe_str(prompt_m)
                lyrics = _safe_str(lyrics_m)
            except Exception:
                self.stats["bad_mel"] += 1
                self.stats["skipped"] += 1
                if self.strict:
                    raise
                continue

            if not self._accept_text_rules(prompt, lyrics):
                self.stats["missing_text"] += 1
                self.stats["skipped"] += 1
                continue

            item_id = _make_item_id(str(mel_pt), prompt, lyrics)
            self.items.append(
                BelelMelItem(
                    mel_path=str(mel_pt),
                    prompt=prompt,
                    lyrics=lyrics,
                    meta=meta,
                    item_id=item_id,
                    integrity="ok",
                    mel_frames=mel_frames,
                )
            )

    def _index_engine_layout(self) -> None:
        for mel_pt in sorted(self.mels_dir.glob("*.pt")):
            self.stats["indexed"] += 1

            stem = mel_pt.stem
            wav_sidecar = self.root / f"{stem}.json"

            if not mel_pt.exists():
                self.stats["missing_file"] += 1
                self.stats["skipped"] += 1
                if self.strict:
                    raise FileNotFoundError(f"Missing mel file: {mel_pt}")
                continue

            # Load mel pt + extract text/meta
            try:
                obj = _load_pt(mel_pt)
                mel_prompt, mel_lyrics, mel_meta = _extract_text_meta_from_mel_pt(obj)
                mel_meta = mel_meta if isinstance(mel_meta, dict) else {}

                mel_frames: Optional[int] = None
                if self.validate_mels:
                    mel = _extract_mel_tensor(obj, mel_pt, expected_bins=self.expected_bins)
                    mel_frames = int(mel.shape[-1])
                else:
                    mel_frames = None
            except Exception:
                self.stats["bad_mel"] += 1
                self.stats["skipped"] += 1
                if self.strict:
                    raise
                continue

            # Load wav sidecar fallback
            wav_meta: Dict[str, Any] = {}
            if wav_sidecar.exists():
                wav_meta = _safe_read_json(wav_sidecar)
            else:
                wav_meta = {}

            wav_prompt = _safe_str(wav_meta.get("prompt", ""))
            wav_lyrics = _safe_str(wav_meta.get("lyrics", ""))

            prompt = _resolve_field_priority(_safe_str(mel_prompt), wav_prompt)
            lyrics = _resolve_field_priority(_safe_str(mel_lyrics), wav_lyrics)

            meta = _merge_meta(wav_meta if isinstance(wav_meta, dict) else {}, mel_meta if isinstance(mel_meta, dict) else {})
            meta = _normalize_meta(meta)

            if not self._accept_text_rules(prompt, lyrics):
                self.stats["missing_text"] += 1
                self.stats["skipped"] += 1
                continue

            item_id = _make_item_id(str(mel_pt), prompt, lyrics)
            self.items.append(
                BelelMelItem(
                    mel_path=str(mel_pt),
                    prompt=prompt,
                    lyrics=lyrics,
                    meta=meta,
                    item_id=item_id,
                    integrity="ok",
                    mel_frames=mel_frames,
                )
            )

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[BelelMelItem]:
        for it in self.items:
            yield it

    def as_list(self) -> List[BelelMelItem]:
        return list(self.items)

    # ----------------------------
    # Reproducibility + diagnostics
    # ----------------------------

    def fingerprint(self) -> str:
        """
        Stable fingerprint of dataset contents for reproducibility / benchmark discipline.
        """
        joined = "|".join(it.item_id for it in self.items)
        return hashlib.sha1(joined.encode("utf-8")).hexdigest()

    def summary(self) -> Dict[str, Any]:
        """
        Lightweight inspection for sanity checks.
        """
        n = len(self.items)
        with_text = sum(1 for it in self.items if ((it.prompt or "").strip() or (it.lyrics or "").strip()))
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
            "strict_provenance": bool(self.strict_provenance),
            "allow_empty_lyrics": bool(self.allow_empty_lyrics),
            "validate_mels": bool(self.validate_mels),
            "fingerprint": self.fingerprint(),
            "stats": dict(self.stats),
        }

    def report(self) -> str:
        """
        Human-readable dataset health report (useful when debugging corpora).
        """
        s = self.summary()
        st = s["stats"]
        lines = [
            f"BelelMelFolder report",
            f"root: {s['root']}",
            f"layout: {'engine' if s['engine_layout'] else ('manifest' if s['manifest'] else 'plain')}",
            f"count: {s['count']}  (with_text: {s['with_text']})",
            f"fingerprint: {s['fingerprint']}",
            f"rules: require_text={s['require_text']} strict_provenance={s['strict_provenance']} allow_empty_lyrics={s['allow_empty_lyrics']} strict={s['strict']}",
            f"validation: validate_mels={s['validate_mels']} expected_bins={s['expected_bins']}",
            f"indexed={st.get('indexed',0)} accepted={st.get('accepted',0)} skipped={st.get('skipped',0)} missing_file={st.get('missing_file',0)} bad_mel={st.get('bad_mel',0)} missing_text={st.get('missing_text',0)} bad_manifest={st.get('bad_manifest',0)}",
        ]
        return "\n".join(lines)
