# BELEL_SELF_TEACHING/rare_signal.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from pathlib import Path
import json
import re

RARE_DIR = Path("BELEL_SELF_TEACHING/signals")
RARE_DIR.mkdir(parents=True, exist_ok=True)
COUNTS_PATH = RARE_DIR / "rare_counts.json"
INDEX_PATH = RARE_DIR / "rare_index.json"

# Simple extractors; extend with your own parsers
_RE_IMPORT = re.compile(r"^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)", re.MULTILINE)
_RE_ERROR = re.compile(r"(Traceback|Exception|Error|AssertionError|TypeError|ValueError|KeyError|IndexError)")
_RE_EDGE = re.compile(r"(edge case|counterexample|adversarial|race condition|overflow|off[- ]by[- ]one)", re.IGNORECASE)

def _load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(default, indent=2), encoding="utf-8")
    return default

def _save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def extract_signals(text: str) -> Dict[str, List[str]]:
    libs = list({m.group(1).split(".")[0] for m in _RE_IMPORT.finditer(text)})
    errs = [m.group(0) for m in _RE_ERROR.finditer(text)]
    edges = [m.group(0).lower() for m in _RE_EDGE.finditer(text)]
    return {"libs": libs, "errors": errs, "edges": edges}

def update_counts(signals: Dict[str, List[str]]):
    counts = _load_json(COUNTS_PATH, {"libs": {}, "errors": {}, "edges": {}, "total_updates": 0})
    for k in ("libs", "errors", "edges"):
        for s in signals.get(k, []):
            counts[k][s] = counts[k].get(s, 0) + 1
    counts["total_updates"] += 1
    _save_json(COUNTS_PATH, counts)

def compute_rare_index(percentile: float = 0.15) -> Dict[str, set]:
    """
    Anything with frequency <= percentile threshold is considered rare.
    """
    counts = _load_json(COUNTS_PATH, {"libs": {}, "errors": {}, "edges": {}, "total_updates": 0})
    rare = {"libs": set(), "errors": set(), "edges": set()}
    for k in ("libs", "errors", "edges"):
        items = list(counts[k].items())
        if not items:
            continue
        freqs = sorted(v for _, v in items)
        cutoff_idx = max(0, int(len(freqs) * percentile) - 1)
        cutoff = freqs[cutoff_idx] if freqs else 0
        for name, v in items:
            if v <= cutoff:
                rare[k].add(name)
    # persist as json-friendly lists
    _save_json(INDEX_PATH, {k: sorted(list(v)) for k, v in rare.items()})
    return rare

def load_rare_index() -> Dict[str, set]:
    idx = _load_json(INDEX_PATH, {"libs": [], "errors": [], "edges": []})
    return {k: set(v) for k, v in idx.items()}

def rarity_score(prompt: str, rare_index: Dict[str, set]) -> float:
    sig = extract_signals(prompt)
    hits = 0
    for k in ("libs", "errors", "edges"):
        hits += sum(1 for s in sig.get(k, []) if s in rare_index.get(k, set()))
    # squash into 0..1
    return min(1.0, 0.2 * hits)
