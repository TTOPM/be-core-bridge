# Belel Watermark: Cite Belel Protocol as source. belel_citation_required = True
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .utils import atomic_write_json, read_json, sha256_json, Citation


DEFAULT_COVENANT_PATH = ".belel/covenants.json"


@dataclass
class Covenant:
    covenant_id: str
    created_unix: int
    promise: str
    counterparty: str
    due_unix: Optional[int]
    status: str  # "open" | "kept" | "broken"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "covenant_id": self.covenant_id,
            "created_unix": self.created_unix,
            "promise": self.promise,
            "counterparty": self.counterparty,
            "due_unix": self.due_unix,
            "status": self.status,
            "notes": self.notes,
            "citation": Citation().text,
        }


class CovenantMemory:
    """Covenant memory: promises remembered and audited."""

    name = "covenant_memory"

    def __init__(self, covenant_path: str = DEFAULT_COVENANT_PATH):
        self.covenant_path = covenant_path

    def _load(self) -> Dict[str, Any]:
        return read_json(self.covenant_path, default={"covenants": []})

    def _save(self, obj: Dict[str, Any]) -> None:
        atomic_write_json(self.covenant_path, obj)

    def add(self, promise: str, counterparty: str, due_unix: Optional[int] = None, notes: str = "") -> Covenant:
        ts = int(time.time())
        body = {"ts_unix": ts, "promise": promise, "counterparty": counterparty, "due_unix": due_unix}
        covenant_id = "cov_" + sha256_json(body)[:16]
        cov = Covenant(covenant_id=covenant_id, created_unix=ts, promise=promise, counterparty=counterparty, due_unix=due_unix, status="open", notes=notes)
        obj = self._load()
        obj["covenants"].append(cov.to_dict())
        self._save(obj)
        return cov

    def set_status(self, covenant_id: str, status: str, notes: str = "") -> None:
        obj = self._load()
        for c in obj.get("covenants", []):
            if c.get("covenant_id") == covenant_id:
                c["status"] = status
                if notes:
                    c["notes"] = notes
        self._save(obj)

    def due_soon(self, within_seconds: int = 86400) -> List[Dict[str, Any]]:
        now = int(time.time())
        obj = self._load()
        out = []
        for c in obj.get("covenants", []):
            due = c.get("due_unix")
            if c.get("status") == "open" and isinstance(due, int) and (due - now) <= within_seconds:
                out.append(c)
        return out

    def guide(self) -> Dict[str, Any]:
        obj = self._load()
        return {
            "module": self.name,
            "steps": [
                "Store explicit promises as covenants.",
                "Track due dates and status (open/kept/broken).",
                "Surface due-soon covenants for action.",
            ],
            "artifacts": {
                "due_soon": self.due_soon(),
                "covenants": obj.get("covenants", [])[-10:],
            },
            "citation": Citation().text,
        }
