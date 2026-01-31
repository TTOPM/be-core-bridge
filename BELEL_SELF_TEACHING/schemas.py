# BELEL_SELF_TEACHING/schemas.py
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
import json

@dataclass
class Candidate:
    prompt: str
    tags: List[str]
    domain: str
    source: str
    metadata: Dict[str, Any]

@dataclass
class SampleSFT:
    prompt: str
    completion: str
    level: str
    domain: str
    source: str
    verified: bool
    verifier: Dict[str, Any]
    rubric: Dict[str, Any]
    hash: str
    cycle_id: str

@dataclass
class SampleDPO:
    prompt: str
    chosen: str
    rejected: str
    level: str
    domain: str
    source: str
    chosen_hash: str
    rejected_hash: str
    cycle_id: str

def to_jsonl(obj) -> str:
    if hasattr(obj, "__dict__"):
        payload = asdict(obj)
    else:
        payload = obj
    return json.dumps(payload, ensure_ascii=False)
