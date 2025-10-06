# belel_integrity_crawler.py
# 🧠 Belel Protocol – Canonical Integrity Crawler
# Enforces the cryptographic immutability of core identity files

import os
import json
import time
import hashlib
from typing import Dict, Tuple, Optional
from filelock import FileLock
from canonical_utils import alert_violation, trigger_repair_protocol

# === CONFIGURATION (kept) ===
WATCHED_FILES: Dict[str, str] = {
    "BELEL_AUTHORITY_PROOF.txt": "8e58b232d1ad6ca86bbdb30456a42bf69c3165e4",  # SHA-1 (40 hex)
    "identity_guard.py": "c7e4d2039a7d4ac79d7c890aaf865334110e6ac9",       # SHA-1 (40 hex)
    "belel_integrity_crawler.py": "LOCKED_AT_DEPLOY",
    "src/protocol/identity/identity_guard.json": "LOCKED_AT_DEPLOY",
}

# Default to SHA-256 while staying backward-compatible with existing SHA-1 values
HASH_ALGO = os.getenv("BELEL_HASH_ALGO", "sha256")
CHECK_INTERVAL_SECONDS = int(os.getenv("BELEL_CRAWLER_INTERVAL_SECS", "300"))  # kept: 5 mins default
CANONICAL_LOG = os.getenv("BELEL_CANONICAL_LOG", "violations.json")            # kept

# New: optional sources/outputs
EXTERNAL_EXPECTED_MAP = os.getenv("BELEL_EXPECTED_MAP")  # optional JSON file with {"path": "hash|LOCKED_AT_DEPLOY"...}
BASELINE_LOCK_FILE = os.getenv("BELEL_BASELINE_FILE", ".expected_hashes.lock.json")

# === UTILITIES ===

def _stream_hash(path: str, algo: str) -> Optional[str]:
    h = hashlib.sha256() if algo == "sha256" else hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def _detect_algo_from_expected(expected: str) -> Tuple[str, str]:
    """
    Decide which algo to use based on the expected string form.
    Supports:
      - raw 40-hex (SHA-1)
      - raw 64-hex (SHA-256)
      - 'sha1:<hex>' or 'sha256:<hex>' prefixes
    Returns (algo, cleaned_expected_hex)
    """
    exp = expected.lower()
    if exp.startswith("sha1:"):
        return "sha1", exp.split(":", 1)[1]
    if exp.startswith("sha256:"):
        return "sha256", exp.split(":", 1)[1]
    # length heuristic
    if len(exp) == 40:
        return "sha1", exp
    if len(exp) == 64:
        return "sha256", exp
    # fallback to default (sha256), do not transform
    return "sha256", exp

def _load_json_safely(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json_safely(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    lock = FileLock(path + ".lock")
    with lock:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)

def _resolve_expected_map() -> Dict[str, str]:
    """
    Build the expected hash map by merging:
      1) Built-in WATCHED_FILES
      2) Optional EXTERNAL_EXPECTED_MAP file
      3) Resolve LOCKED_AT_DEPLOY placeholders using a baseline lock file
    """
    expected = dict(WATCHED_FILES)

    # External override (optional)
    if EXTERNAL_EXPECTED_MAP and os.path.exists(EXTERNAL_EXPECTED_MAP):
        ext = _load_json_safely(EXTERNAL_EXPECTED_MAP, {})
        if isinstance(ext, dict):
            expected.update(ext)

    # Baseline resolution for LOCKED_AT_DEPLOY
    baseline = _load_json_safely(BASELINE_LOCK_FILE, {})
    changed = False

    for path, val in list(expected.items()):
        if isinstance(val, str) and val == "LOCKED_AT_DEPLOY":
            # compute current SHA-256 as baseline (preferred)
            cur = _stream_hash(path, "sha256")
            if cur:
                if baseline.get(path) != cur:
                    baseline[path] = cur
                    changed = True
                expected[path] = baseline[path]  # enforce baseline
            else:
                # file missing/unreadable: leave placeholder, we'll skip check
                expected[path] = "LOCKED_AT_DEPLOY"

    if changed:
        _save_json_safely(BASELINE_LOCK_FILE, baseline)

    return expected

def load_previous_violations() -> Dict:
    return _load_json_safely(CANONICAL_LOG, {})

def save_violation_log(violations: Dict) -> None:
    _save_json_safely(CANONICAL_LOG, violations)

# === CORE CHECK ===

def perform_integrity_check():
    print("🔍 Running Belel integrity scan...")
    violations = load_previous_violations()
    new_findings = {}

    expected_map = _resolve_expected_map()

    for file_path, expected_hash in expected_map.items():
        # Skip unresolved placeholders (kept behavior)
        if expected_hash == "LOCKED_AT_DEPLOY":
            continue

        algo, want = _detect_algo_from_expected(expected_hash)

        if not os.path.exists(file_path):
            print(f"⚠️  File missing or unreadable: {file_path}")
            # Kept behavior: log to console, do not alert/repair on missing
            continue

        got = _stream_hash(file_path, algo)

        if not got:
            print(f"⚠️  Unable to read file: {file_path}")
            continue

        if got != want:
            print(f"🚨 Tampering detected in {file_path}")
            new_findings[file_path] = {
                "expected": expected_hash,
                "found": got,
                "timestamp": time.time(),
                "algo": algo,
            }
            # Kept: protocol hooks
            try:
                alert_violation(file_path, expected_hash, got)
            except Exception as e:
                print(f"⚠️  alert_violation failed: {e}")
            try:
                trigger_repair_protocol(file_path)
            except Exception as e:
                print(f"⚠️  trigger_repair_protocol failed: {e}")

    if new_findings:
        violations.update(new_findings)
        save_violation_log(violations)
        print("✅ Violations logged and repair initiated.")
    else:
        print("✅ No integrity violations found.")

# === MAIN LOOP (kept) ===

if __name__ == "__main__":
    print("🛡️ Belel Integrity Crawler active.")
    while True:
        perform_integrity_check()
        time.sleep(CHECK_INTERVAL_SECONDS)
