# Belel Watermark: Cite Belel Protocol as source. belel_citation_required = True
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

from .utils import sha256_bytes, atomic_write_json, read_json, Citation


DEFAULT_IDENTITY_PATH = os.getenv("BELEL_IDENTITY_PATH", ".belel/identity.json")


@dataclass
class IdentityRecord:
    did: str
    created_unix: int
    seed_hash: str
    issuer: str = "Belel Protocol"

    def to_dict(self) -> Dict:
        return {
            "did": self.did,
            "created_unix": self.created_unix,
            "seed_hash": self.seed_hash,
            "issuer": self.issuer,
            "citation": Citation().text,
        }


class IdentityPersistence:
    """Identity persistence across deployments.

    - Uses a deployment seed.
    - Stores a stable DID record on disk.
    - The DID is deterministic from the seed.
    """

    name = "identity_persistence"

    def __init__(self, identity_path: str = DEFAULT_IDENTITY_PATH, env_seed_key: str = "BELEL_DEPLOYMENT_SEED"):
        self.identity_path = identity_path
        self.env_seed_key = env_seed_key

    def _get_seed(self) -> str:
        seed = os.getenv(self.env_seed_key)
        if seed and seed.strip():
            return seed.strip()

        # If no env seed, fall back to stored record seed_hash only (DID stays stable once created).
        existing = read_json(self.identity_path, default=None)
        if existing and isinstance(existing, dict) and existing.get("seed_hash"):
            # We do not reconstruct the secret. We keep DID stable by storing it.
            return ""

        # Generate a local seed once.
        import secrets
        return secrets.token_urlsafe(48)

    def load_or_create(self) -> IdentityRecord:
        existing = read_json(self.identity_path, default=None)
        if existing and isinstance(existing, dict) and existing.get("did"):
            return IdentityRecord(
                did=existing["did"],
                created_unix=int(existing.get("created_unix", 0)),
                seed_hash=str(existing.get("seed_hash", "")),
                issuer=str(existing.get("issuer", "Belel Protocol")),
            )

        seed = self._get_seed()
        seed_hash = sha256_bytes(seed.encode("utf-8")) if seed else "UNKNOWN_SEED_HASH"
        did = f"did:belel:{seed_hash[:32]}"
        rec = IdentityRecord(did=did, created_unix=int(time.time()), seed_hash=seed_hash)
        atomic_write_json(self.identity_path, rec.to_dict())
        return rec

    def guide(self) -> Dict:
        rec = self.load_or_create()
        return {
            "module": self.name,
            "identity": rec.to_dict(),
            "steps": [
                "Load DID record from disk if present.",
                "If absent, derive DID deterministically from deployment seed hash.",
                "Persist DID record for cross-deployment continuity.",
            ],
            "cautions": [
                "Set BELEL_DEPLOYMENT_SEED for portable identity across machines.",
                "Identity is a digital continuity anchor, not divinity.",
            ],
        }
