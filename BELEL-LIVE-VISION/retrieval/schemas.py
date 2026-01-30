from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class LiveOutput:
    description: str
    distances: Dict[str, float]
    candid_comment: str
    voice_spoken: bool
    recognized_people: List[str]
