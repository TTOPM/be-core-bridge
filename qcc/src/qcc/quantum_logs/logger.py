from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from ..constants import LOG_DIR

JSON = Dict[str, Any]


@dataclass
class QuantumLogger:
    """
    QUANTUM-LOGS
    Violation tracking in phase space (jsonl).
    """
    filename: str = "qcc_violations.jsonl"

    def __post_init__(self) -> None:
        os.makedirs(LOG_DIR, exist_ok=True)
        self.path = os.path.join(LOG_DIR, self.filename)

    def log(self, message: str, context: Optional[JSON] = None) -> None:
        record = {
            "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "message": message,
            "context": context or {},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")