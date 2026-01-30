from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List


def append_research_log(base_dir: Path, entry: Dict[str, Any]) -> Path:
    log_path = base_dir / "research_ingestion" / "research_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    data: List[Dict[str, Any]] = []
    if log_path.exists():
        try:
            data = json.loads(log_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []

    data.append(entry)
    log_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return log_path
