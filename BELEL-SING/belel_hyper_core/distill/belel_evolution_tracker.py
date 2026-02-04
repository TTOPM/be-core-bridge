from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Iterable

@dataclass
class BelelEvolutionItem:
    prompt: str
    lyrics: str
    artifact_path: str
    score: float
    utc: str

class BelelEvolutionTracker:
    def __init__(self, root: str = "logs/belel_evolution"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "evolution.jsonl"

    def _utc_now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def log(self, prompt: str, lyrics: str, artifact_path: str, score: float):
        item = BelelEvolutionItem(
            prompt=prompt,
            lyrics=lyrics,
            artifact_path=artifact_path,
            score=float(score),
            utc=self._utc_now(),
        )
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")

    def select(self, min_score: float = 8.0, limit: int = 512) -> list[BelelEvolutionItem]:
        if not self.log_path.exists():
            return []
        items: list[BelelEvolutionItem] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(line)
                if float(obj.get("score", 0)) >= min_score:
                    items.append(BelelEvolutionItem(**obj))
            except Exception:
                continue
        # newest first
        items = list(reversed(items))
        return items[:limit]
