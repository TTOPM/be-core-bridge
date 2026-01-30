from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

from .policies import MutationPolicy, default_policy


def _registry_path(base_dir: Path) -> Path:
    p = base_dir / "mutation_registry" / "mutation_registry.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def register_mutation(
    base_dir: Path,
    mutation_id: str,
    description: str,
    files_touched: List[str],
    policy: Optional[MutationPolicy] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    reg = _registry_path(base_dir)
    data: List[Dict[str, Any]] = []
    if reg.exists():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []

    pol = policy or default_policy()
    entry = {
        "mutation_id": mutation_id,
        "description": description,
        "files_touched": files_touched,
        "policy": asdict(pol),
        "metadata": metadata or {},
    }
    data.append(entry)
    reg.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return reg


def list_mutations(base_dir: Path) -> List[Dict[str, Any]]:
    reg = _registry_path(base_dir)
    if not reg.exists():
        return []
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []
