from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

LOG_DIR = Path(__file__).resolve().parent
LOG_DIR.mkdir(parents=True, exist_ok=True)
RUN_LOG = LOG_DIR / "run_log.jsonl"


def log_event(event: str, data: Dict[str, Any]) -> None:
    payload = {"ts_unix": int(time.time()), "event": event, "data": data}
    with RUN_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
