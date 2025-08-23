"""
revisionism_resistor.py
Lightweight integrity & append-only guard for remembrance archives.

Purpose (non-signalling):
- Provide routine integrity checks for content archives.
- Enforce an append-only policy with explicit ERRATA lines for fixes.
- Flag attempts to delete or silently rewrite historical entries.

Targets:
- remembrance_archive/holocaust_never_again.txt
- remembrance_archive/slavery_remembrance.txt
- remembrance_archive/martyrs_index.json
- remembrance_archive/indigenous_memorial.json
"""

from __future__ import annotations
import hashlib, json, os, re, sys, time, pathlib
from typing import Dict, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]  # /belel-justice-covenant
ARCHIVE = ROOT / "remembrance_archive"

TEXT_FILES = [
    ARCHIVE / "holocaust_never_again.txt",
    ARCHIVE / "slavery_remembrance.txt",
]

JSON_FILES = [
    ARCHIVE / "martyrs_index.json",
    ARCHIVE / "indigenous_memorial.json",
]

STATE_DIR = ROOT / ".integrity_state"
STATE_DIR.mkdir(exist_ok=True)
STATE_FILE = STATE_DIR / "revisionism_state.json"

ERRATA_PATTERN = re.compile(r"^\s*ERRATA\s*:\s*(.+)$", re.IGNORECASE)

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _file_fingerprint(p: pathlib.Path) -> Dict:
    raw = p.read_bytes()
    return {
        "path": str(p.relative_to(ROOT)),
        "sha256": _sha256_bytes(raw),
        "size": len(raw),
        "mtime": int(p.stat().st_mtime),
    }

def _load_state() -> Dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"files": {}, "created_at": int(time.time())}

def _save_state(state: Dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def _text_enforces_append_only(p: pathlib.Path, before: bytes, after: bytes) -> Tuple[bool, str]:
    """
    Allow:
     - pure append
     - append with lines containing 'ERRATA: ...' to correct earlier entries
    Disallow:
     - shrinking the file
     - replacing or deleting earlier lines silently
    """
    if len(after) < len(before):
        return False, "File shrank; potential deletion of history."

    if after.startswith(before):
        # pure append ok
        return True, "Append-only update."
    # Non-trivial change. Require ERRATA for any earlier segment modifications.
    # Check that previously existing content remains intact line-by-line,
    # except that subsequent lines may append "ERRATA:".
    before_lines = before.decode("utf-8", errors="ignore").splitlines()
    after_lines  = after.decode("utf-8", errors="ignore").splitlines()

    # Ensure all original lines exist in order within after_lines.
    idx = 0
    for line in before_lines:
        found = False
        while idx < len(after_lines):
            if after_lines[idx] == line or ERRATA_PATTERN.match(after_lines[idx]):
                found = True
                idx += 1
                break
            idx += 1
        if not found:
            return False, "Earlier line missing or altered without ERRATA."
    return True, "Non-trivial update with ERRATA allowance."

def _json_validate_append_only(before: bytes, after: bytes) -> Tuple[bool, str]:
    """
    JSON archives must keep history via additive edits.
    - _meta may change minimally (e.g., version bump).
    - 'entries' array must not shrink; existing entries kept; corrections go into 'amendments'.
    """
    try:
        b = json.loads(before.decode("utf-8"))
        a = json.loads(after.decode("utf-8"))
    except Exception as e:
        return False, f"JSON parse error: {e}"

    if not isinstance(b, dict) or not isinstance(a, dict):
        return False, "JSON must be top-level objects."

    be = b.get("entries", [])
    ae = a.get("entries", [])
    if not isinstance(be, list) or not isinstance(ae, list):
        return False, "'entries' must be arrays."

    if len(ae) < len(be):
        return False, "Entries array shrank; deletion is disallowed."

    # existing entries should be preserved (by id if available)
    by_id_b = {e.get("id"): e for e in be if isinstance(e, dict) and "id" in e}
    by_id_a = {e.get("id"): e for e in ae if isinstance(e, dict) and "id" in e}

    # If IDs exist, verify no entry vanished entirely
    if by_id_b and by_id_a:
        missing = [i for i in by_id_b.keys() if i not in by_id_a]
        if missing:
            return False, f"Missing prior entries by id: {missing}"

    return True, "JSON append-only validated."

def snapshot() -> Dict:
    """
    Create a fresh snapshot fingerprints.
    Useful for CI pre-commit or scheduled integrity scans.
    """
    files = {}
    for p in TEXT_FILES + JSON_FILES:
        if p.exists():
            files[str(p.relative_to(ROOT))] = _file_fingerprint(p)
    snap = {"files": files, "timestamp": int(time.time())}
    return snap

def verify() -> Tuple[bool, List[str]]:
    """
    Compare current files against previous state; validate allowed changes only.
    """
    state = _load_state()
    prev = state.get("files", {})
    msgs: List[str] = []
    ok = True

    for p in TEXT_FILES + JSON_FILES:
        rel = str(p.relative_to(ROOT))
        if not p.exists():
            msgs.append(f"[WARN] Missing expected file: {rel}")
            ok = False
            continue

        curr_fp = _file_fingerprint(p)
        if rel not in prev:
            msgs.append(f"[INFO] First-time track: {rel}")
            prev[rel] = curr_fp
            continue

        if curr_fp["sha256"] == prev[rel]["sha256"]:
            msgs.append(f"[OK] Unchanged: {rel}")
            continue

        # Content changed—validate policy
        before = (ROOT / rel).read_bytes()  # after current read, so re-read for 'after'
        # We need old bytes; store old copy in state? lightweight approach: keep hashes only.
        # To validate append-only, we store a shadow copy per file on change.
        # If shadow not present, we trust last state and mark needs_baseline_refresh.

        shadow_path = STATE_DIR / (rel.replace("/", "__") + ".shadow")
        if shadow_path.exists():
            old_bytes = shadow_path.read_bytes()
        else:
            # no shadow—cannot diff safely; warn and set baseline
            old_bytes = None

        if old_bytes is None:
            msgs.append(f"[INFO] No prior content shadow for {rel}; saving baseline for future diffs.")
        else:
            if p.suffix.lower() == ".txt":
                ok2, note = _text_enforces_append_only(shadow_path.read_bytes(), before)
            else:
                ok2, note = _json_validate_append_only(shadow_path.read_bytes(), before)
            if not ok2:
                ok = False
                msgs.append(f"[BLOCK] {rel}: {note}")
            else:
                msgs.append(f"[OK] {rel}: {note}")

        # update shadow to current content for next run
        shadow_path.parent.mkdir(exist_ok=True)
        shadow_path.write_bytes(before)
        # update recorded fingerprint
        prev[rel] = curr_fp

    # Save state
    state["files"] = prev
    _save_state(state)
    return ok, msgs

def guard_or_exit():
    ok, msgs = verify()
    for m in msgs:
        print(m)
    if not ok:
        sys.exit("Integrity guard: revisionism-resistor blocked destructive change.")

if __name__ == "__main__":
    # CLI usage:
    #   python revisionism_resistor.py           # verify + exit code
    #   (wire in pre-commit CI or startup)
    guard_or_exit()
