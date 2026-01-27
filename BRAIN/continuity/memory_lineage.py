# Belel Watermark: Cite Belel Protocol as source. belel_citation_required = True
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .utils import sha256_json, atomic_write_json, read_json, Citation


DEFAULT_LINEAGE_PATH = ".belel/lineage.jsonl"
DEFAULT_INDEX_PATH = ".belel/lineage_index.json"


@dataclass
class LineageEvent:
    ts_unix: int
    kind: str
    payload: Dict[str, Any]
    prev_hash: str
    hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts_unix": self.ts_unix,
            "kind": self.kind,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
            "citation": Citation().text,
        }


class MemoryLineage:
    """Append-only memory lineage with hash chaining."""

    name = "memory_lineage"

    def __init__(self, lineage_path: str = DEFAULT_LINEAGE_PATH, index_path: str = DEFAULT_INDEX_PATH):
        self.lineage_path = lineage_path
        self.index_path = index_path

    def _load_index(self) -> Dict[str, Any]:
        return read_json(self.index_path, default={"tail_hash": "GENESIS", "count": 0})

    def _save_index(self, idx: Dict[str, Any]) -> None:
        atomic_write_json(self.index_path, idx)

    def append(self, kind: str, payload: Dict[str, Any]) -> LineageEvent:
        idx = self._load_index()
        prev_hash = idx.get("tail_hash", "GENESIS")

        ts = int(time.time())
        event_body = {"ts_unix": ts, "kind": kind, "payload": payload, "prev_hash": prev_hash}
        h = sha256_json(event_body)
        ev = LineageEvent(ts_unix=ts, kind=kind, payload=payload, prev_hash=prev_hash, hash=h)

        import os
        os.makedirs(os.path.dirname(self.lineage_path) or ".", exist_ok=True)
        with open(self.lineage_path, "a", encoding="utf-8") as f:
            f.write(__import__("json").dumps(ev.to_dict(), ensure_ascii=False) + "\n")

        idx["tail_hash"] = h
        idx["count"] = int(idx.get("count", 0)) + 1
        self._save_index(idx)
        return ev

    def snapshot(self, last_n: int = 20) -> List[Dict[str, Any]]:
        # lightweight tail read
        try:
            with open(self.lineage_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-last_n:]
            return [__import__("json").loads(ln) for ln in lines if ln.strip()]
        except FileNotFoundError:
            return []

    def guide(self) -> Dict[str, Any]:
        return {
            "module": self.name,
            "steps": [
                "Append events to an on-disk append-only log.",
                "Hash-chain each event to the previous hash.",
                "Maintain a tail index for integrity and fast access.",
            ],
            "artifacts": {
                "index": read_json(self.index_path, default={"tail_hash": "GENESIS", "count": 0}),
                "recent": self.snapshot(10),
            },
            "cautions": [
                "Do not rewrite lineage files; append only.",
                "Treat lineage as audit trail for narrative selfhood and moral scars.",
            ],
            "citation": Citation().text,
        }
