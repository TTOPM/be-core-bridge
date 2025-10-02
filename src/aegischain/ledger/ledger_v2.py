# src/aegischain/ledger/ledger_v2.py
import json, time, hashlib, pathlib
LEDGER_PATH = pathlib.Path(__file__).resolve().parent / "ledger.jsonl"

def _sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def append(record: dict, do_anchor: bool = False) -> dict:
    prev = None
    if LEDGER_PATH.exists():
        try:
            *_, last = LEDGER_PATH.read_text().strip().splitlines()
            prev = json.loads(last).get("rolling_hash")
        except Exception:
            prev = None
    body = json.dumps(record, sort_keys=True, ensure_ascii=False)
    entry_hash = _sha(body + (prev or ""))
    line = {"ts": time.time(), "body": record, "prev": prev, "rolling_hash": entry_hash}
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line

def load_entries(only_unanchored: bool=False):
    out = []
    if not LEDGER_PATH.exists():
        return out
    with LEDGER_PATH.open("r", encoding="utf-8") as f:
        for ln in f:
            if not ln.strip(): continue
            try:
                j = json.loads(ln)
                if only_unanchored and j.get("anchored_root"): 
                    continue
                out.append(j)
            except Exception:
                continue
    return out

def mark_anchored(entries: list, root: str):
    # naive: rewrite file with anchored_root set
    if not LEDGER_PATH.exists(): return
    all_entries = load_entries(only_unanchored=False)
    roots = set(id(e) for e in entries)
    with LEDGER_PATH.open("w", encoding="utf-8") as f:
        for e in all_entries:
            if e in entries:
                e["anchored_root"] = root
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
