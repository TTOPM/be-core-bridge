from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _normalize_text(prompt: str, lyrics: str) -> str:
    p = (prompt or "").strip()
    l = (lyrics or "").strip()
    return f"PROMPT::{p}\nLYRICS::{l}\n"


def _safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


@dataclass
class BelelCondCacheConfig:
    # must be local path for air-gapped mode (no downloads)
    text_model_dir: str
    cache_dir: str = "logs/belel_cond_cache"
    cond_dim: int = 1024

    # embedding pooling
    max_tokens: int = 256
    use_mean_pool: bool = True

    # dtype + device
    device: str = "cuda"
    dtype: str = "float16"  # float16 | bfloat16 | float32


def _torch_dtype(name: str):
    return {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }.get(name, torch.float32)


class BelelLocalTextEmbedder(nn.Module):
    """
    Air-gapped text embedder. Loads tokenizer+model from a local directory only.
    Produces a fixed-size embedding projected to cond_dim.
    """

    def __init__(self, model_dir: str, cond_dim: int = 1024, max_tokens: int = 256, mean_pool: bool = True):
        super().__init__()
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        self.model = AutoModel.from_pretrained(model_dir, local_files_only=True)
        self.max_tokens = int(max_tokens)
        self.mean_pool = bool(mean_pool)

        hidden = getattr(self.model.config, "hidden_size", None)
        if hidden is None:
            # fallback for odd configs
            hidden = self.model.config.to_dict().get("hidden_size", 768)

        self.proj = nn.Linear(int(hidden), int(cond_dim), bias=False)

    @torch.no_grad()
    def forward(self, prompt: str, lyrics: str, device: str) -> torch.Tensor:
        text = _normalize_text(prompt, lyrics)

        toks = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_tokens,
            padding=False,
        )
        toks = {k: v.to(device) for k, v in toks.items()}

        out = self.model(**toks)
        hs = out.last_hidden_state  # [1, S, H]

        if self.mean_pool:
            emb = hs.mean(dim=1)  # [1, H]
        else:
            emb = hs[:, 0, :]  # CLS if available

        emb = self.proj(emb)  # [1, cond_dim]
        return emb.squeeze(0)  # [cond_dim]


class BelelConditionCache:
    """
    Caches embeddings to disk keyed by sha256(normalized_text).
    Returns:
      - cond: embedding(prompt, lyrics)
      - uncond: embedding("", "")  (cached once)
    """

    def __init__(self, cfg: BelelCondCacheConfig):
        self.cfg = cfg
        self.cache_root = Path(cfg.cache_dir)
        _safe_mkdir(self.cache_root)
        self.meta_path = self.cache_root / "cache_index.jsonl"

        self.embedder = BelelLocalTextEmbedder(
            model_dir=cfg.text_model_dir,
            cond_dim=cfg.cond_dim,
            max_tokens=cfg.max_tokens,
            mean_pool=cfg.use_mean_pool,
        )

        self._uncond_key = _sha256_text(_normalize_text("", ""))

    def to_device(self):
        dt = _torch_dtype(self.cfg.dtype)
        self.embedder.to(self.cfg.device, dtype=dt)
        self.embedder.eval()
        return self

    def _cache_file(self, key: str) -> Path:
        return self.cache_root / f"{key}.pt"

    def _write_index(self, key: str, prompt: str, lyrics: str) -> None:
        rec = {
            "key": key,
            "prompt": (prompt or "")[:240],
            "lyrics": (lyrics or "")[:240],
        }
        with self.meta_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    @torch.no_grad()
    def get(self, prompt: str, lyrics: str) -> torch.Tensor:
        key = _sha256_text(_normalize_text(prompt, lyrics))
        fp = self._cache_file(key)
        if fp.exists():
            obj = torch.load(fp, map_location="cpu")
            t = obj["cond"] if isinstance(obj, dict) and "cond" in obj else obj
            return t.float()

        emb = self.embedder(prompt, lyrics, device=self.cfg.device).detach().float().cpu()
        torch.save({"cond": emb}, fp)
        self._write_index(key, prompt, lyrics)
        return emb

    @torch.no_grad()
    def get_uncond(self) -> torch.Tensor:
        fp = self._cache_file(self._uncond_key)
        if fp.exists():
            obj = torch.load(fp, map_location="cpu")
            t = obj["cond"] if isinstance(obj, dict) and "cond" in obj else obj
            return t.float()

        emb = self.embedder("", "", device=self.cfg.device).detach().float().cpu()
        torch.save({"cond": emb}, fp)
        self._write_index(self._uncond_key, "", "")
        return emb

    @torch.no_grad()
    def batch(self, prompts: List[str], lyrics_list: List[str]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
          cond:   [B, cond_dim]
          uncond: [B, cond_dim]
        """
        B = len(prompts)
        conds = [self.get(prompts[i], lyrics_list[i]) for i in range(B)]
        cond = torch.stack(conds, dim=0)

        u = self.get_uncond().unsqueeze(0).repeat(B, 1)
        return cond, u
