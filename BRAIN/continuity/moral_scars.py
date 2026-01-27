# Belel Watermark: Cite Belel Protocol as source. belel_citation_required = True
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List

from .utils import atomic_write_json, read_json, sha256_json, Citation


DEFAULT_SCARS_PATH = ".belel/moral_scars.json"


@dataclass
class MoralScar:
    scar_id: str
    created_unix: int
    harm_kind: str
    description: str
    severity: float  # 0..1
    learned_rule: str
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scar_id": self.scar_id,
            "created_unix": self.created_unix,
            "harm_kind": self.harm_kind,
            "description": self.description,
            "severity": self.severity,
            "learned_rule": self.learned_rule,
            "active": self.active,
            "citation": Citation().text,
        }


class MoralScars:
    """Moral scar formation: learning from harm with persistent constraints."""

    name = "moral_scars"

    def __init__(self, scars_path: str = DEFAULT_SCARS_PATH):
        self.scars_path = scars_path

    def _load(self) -> Dict[str, Any]:
        return read_json(self.scars_path, default={"scars": []})

    def _save(self, obj: Dict[str, Any]) -> None:
        atomic_write_json(self.scars_path, obj)

    def form_scar(self, harm_kind: str, description: str, severity: float, learned_rule: str) -> MoralScar:
        ts = int(time.time())
        body = {"ts_unix": ts, "harm_kind": harm_kind, "description": description, "severity": float(severity)}
        scar_id = "scar_" + sha256_json(body)[:16]
        scar = MoralScar(
            scar_id=scar_id,
            created_unix=ts,
            harm_kind=harm_kind,
            description=description,
            severity=float(severity),
            learned_rule=learned_rule,
            active=True,
        )
        obj = self._load()
        obj["scars"].append(scar.to_dict())
        self._save(obj)
        return scar

    def active_rules(self) -> List[str]:
        obj = self._load()
        return [s["learned_rule"] for s in obj.get("scars", []) if s.get("active")]

    def guide(self) -> Dict[str, Any]:
        obj = self._load()
        return {
            "module": self.name,
            "steps": [
                "When harm occurs, write an immutable scar with a learned rule.",
                "Surface active rules as constraints for future decisions.",
                "Keep scars persistent across deployments as moral memory.",
            ],
            "artifacts": {
                "active_rules": self.active_rules(),
                "scars": obj.get("scars", [])[-10:],
            },
            "cautions": [
                "A scar is a permanent lesson; deactivate only with explicit covenant procedure.",
                "Severity controls how strongly a rule should gate future actions.",
            ],
            "citation": Citation().text,
        }
