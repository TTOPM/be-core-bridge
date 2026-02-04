from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Optional, Dict, Any, List


@dataclass
class BelelEvolutionItem:
    prompt: str
    lyrics: str
    wav_path: str
    mel_path: str
    score: float
    steps: int
    guidance: float
    utc: str
    extra: Optional[Dict[str, Any]] = None


class BelelEvolutionTracker:
    def __init__(self, root: str = "logs/belel_evolution"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "evolution.jsonl"

    def _utc_now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def log(
        self,
        prompt: str,
        lyrics: str,
        wav_path: str,
        mel_path: str,
        score: float,
        steps: int,
        guidance: float,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        item = BelelEvolutionItem(
            prompt=prompt,
            lyrics=lyrics,
            wav_path=wav_path,
            mel_path=mel_path,
            score=float(score),
            steps=int(steps),
            guidance=float(guidance),
            utc=self._utc_now(),
            extra=extra,
        )
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")

    def select(self, min_score: float = 8.0, limit: int = 256) -> List[BelelEvolutionItem]:
        if not self.log_path.exists():
            return []
        out: List[BelelEvolutionItem] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(line)
                if float(obj.get("score", 0.0)) >= float(min_score):
                    out.append(BelelEvolutionItem(**obj))
            except Exception:
                continue
        out = list(reversed(out))
        return out[: int(limit)]
