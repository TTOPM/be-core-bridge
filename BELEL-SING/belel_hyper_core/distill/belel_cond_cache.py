from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import json
import hashlib

import torch


@dataclass
class BelelCondCacheConfig:
    """
    Conditioner embedding cache configuration.

    text_model_dir:
      Local HF model directory (air-gapped).

    cache_dir:
      Root directory for cached embeddings.

    cond_dim:
      Expected embedding dimension.

    device:
      torch device used for embedding generation.

    dtype:
      float16 | bfloat16 | float32

    max_tokens:
      Max tokens for conditioning encoder.

    use_mean_pool:
      If True, mean-pool token embeddings.
    """
    text_model_dir: str
    cache_dir: str
    cond_dim: int
    device: str = "cuda"
    dtype: str = "float16"
    max_tokens: int = 256
    use_mean_pool: bool = True


class BelelConditionCache:
    """
    ID-keyed, air-gapped conditioner embedding cache.

    IMPORTANT:
      Cache key is **item_id**, NOT prompt/lyrics text.
      This guarantees:
        - no collisions
        - reproducibility
        - dataset fingerprint alignment
    """

    def __init__(self, cfg: BelelCondCacheConfig):
        self.cfg = cfg
        self.cache_root = Path(cfg.cache_dir)
        self.cache_root.mkdir(parents=True, exist_ok=True)

        self._model = None
        self._tokenizer = None

    # ----------------------------
    # Model loading
    # ----------------------------

    def to_device(self) -> "BelelConditionCache":
        from transformers import AutoTokenizer, AutoModel

        if self._model is not None:
            return self

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.cfg.text_model_dir,
            local_files_only=True,
            use_fast=True,
        )

        self._model = AutoModel.from_pretrained(
            self.cfg.text_model_dir,
            local_files_only=True,
            torch_dtype=getattr(torch, self.cfg.dtype),
        ).to(self.cfg.device)

        self._model.eval()
        return self

    # ----------------------------
    # Cache paths
    # ----------------------------

    def _cond_path(self, item_id: str) -> Path:
        return self.cache_root / f"{item_id}.cond.pt"

    def _uncond_path(self, item_id: str) -> Path:
        return self.cache_root / f"{item_id}.uncond.pt"

    # ----------------------------
    # Encoding
    # ----------------------------

    @torch.no_grad()
    def _encode_text(self, text: str) -> torch.Tensor:
        tok = self._tokenizer(
            text,
            truncation=True,
            max_length=self.cfg.max_tokens,
            return_tensors="pt",
        ).to(self.cfg.device)

        out = self._model(**tok).last_hidden_state  # [1,T,D]

        if self.cfg.use_mean_pool:
            emb = out.mean(dim=1)  # [1,D]
        else:
            emb = out[:, 0]  # CLS

        return emb

    # ----------------------------
    # Public API
    # ----------------------------

    def get(
        self,
        *,
        item_id: str,
        prompt: str,
        lyrics: str,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
          cond_emb, uncond_emb   (CPU tensors)

        Cache key: item_id ONLY.
        """
        cond_path = self._cond_path(item_id)
        uncond_path = self._uncond_path(item_id)

        if cond_path.exists() and uncond_path.exists():
            cond = torch.load(cond_path, map_location="cpu")
            uncond = torch.load(uncond_path, map_location="cpu")
            return cond, uncond

        # Generate embeddings
        self.to_device()

        cond_text = (prompt or "") + ("\n" + lyrics if lyrics else "")
        uncond_text = ""

        cond_emb = self._encode_text(cond_text)
        uncond_emb = self._encode_text(uncond_text)

        # Move to CPU for storage
        cond_cpu = cond_emb.detach().cpu()
        uncond_cpu = uncond_emb.detach().cpu()

        torch.save(cond_cpu, cond_path)
        torch.save(uncond_cpu, uncond_path)

        return cond_cpu, uncond_cpu

    def batch(
        self,
        *,
        item_ids: List[str],
        prompts: List[str],
        lyrics_list: List[str],
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Batch fetch using item_id-aligned caching.
        """
        conds: List[torch.Tensor] = []
        unconds: List[torch.Tensor] = []

        for iid, p, l in zip(item_ids, prompts, lyrics_list):
            c, u = self.get(item_id=iid, prompt=p, lyrics=l)
            conds.append(c)
            unconds.append(u)

        cond = torch.cat(conds, dim=0)
        uncond = torch.cat(unconds, dim=0)

        return cond, uncond
