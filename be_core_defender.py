#!/usr/bin/env python3
"""
be_core_defender.py

Modes:
  - gate  : CI/PR guard. Fast, deterministic, exits with non-zero on violations (when --strict).
  - sweep : Deep scan for scheduled jobs. Produces richer report; can perform optional mirror pings.

Key design:
  - Default behavior is ONE scan and exit (Actions-friendly).
  - Daemon loop only when explicitly requested (--daemon).
"""

import argparse
import os
import shutil
import time
import json
import hashlib
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import requests
from filelock import FileLock
from requests.adapters import HTTPAdapter, Retry

# === Configuration (preserved) ===
PROTECTED_FILES = [
    "BELEL_PROTOCOL_OVERVIEW.md",
    "canonical_config.json",
    "belel_guardian.py",
    "media_sentient_engine.py",
    "mutation_watcher.py",
    "claim_review_publisher.py",
    "concordium_enforcer.py",
]

MIRROR_URLS = [
    "https://github.com/TTOPM/be-core-bridge",
    "https://arweave.net/",
    "https://ipfs.io/ipfs/",
]

BACKUP_DIR = "./backup_mirror"
HASH_STORE = "code_hashes.json"

# Optional env overrides / extras (non-breaking)
DEFAULT_INTERVAL_SECS = int(os.getenv("BELEL_DEFENDER_INTERVAL_SECS", "300"))
WEB3_STORAGE_ENDPOINT = os.getenv("WEB3_STORAGE_ENDPOINT", "https://api.web3.storage/upload")
WEB3_STORAGE_TOKEN = os.getenv("WEB3_STORAGE_TOKEN")  # optional but recommended

# Concurrency lock so scheduled workflows don't collide
DEFENDER_LOCK = os.getenv("BELEL_DEFENDER_LOCK", ".defender.lock")

# Reasonable safety for network calls
REQUEST_TIMEOUT_SECS = float(os.getenv("BELEL_DEFENDER_HTTP_TIMEOUT", "8"))
MAX_FILE_BYTES_FOR_TEXT_SCAN = int(os.getenv("BELEL_DEFENDER_MAX_TEXT_SCAN_BYTES", str(2_000_000)))  # 2MB


# === Helpers ===

def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _requests_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


def hash_file(filepath: str) -> str:
    """Stream SHA-256 to support large files safely."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 128), b""):
            h.update(chunk)
    return h.hexdigest()


def load_hashes() -> Dict[str, str]:
    if not os.path.exists(HASH_STORE):
        return {}
    try:
        with FileLock(HASH_STORE + ".lock"):
            with open(HASH_STORE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
                return {}
    except Exception:
        return {}


def save_hashes(hashes: Dict[str, str]) -> None:
    os.makedirs(os.path.dirname(HASH_STORE) or ".", exist_ok=True)
    tmp = HASH_STORE + ".tmp"
    with FileLock(HASH_STORE + ".lock"):
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(hashes, f, indent=2, ensure_ascii=False)
        os.replace(tmp, HASH_STORE)


def backup_file(filepath: str) -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = os.path.join(BACKUP_DIR, f"{os.path.basename(filepath)}.{timestamp}.bak")
    shutil.copy2(filepath, backup_path)
    return backup_path


def restore_file(filepath: str) -> Optional[str]:
    if not os.path.exists(BACKUP_DIR):
        return None
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith(os.path.basename(filepath) + ".")],
        reverse=True,
    )
    if not backups:
        return None
    latest = os.path.join(BACKUP_DIR, backups[0])
    shutil.copy2(latest, filepath)
    return latest


def read_text_limited(filepath: str) -> str:
    """Read file as text up to MAX_FILE_BYTES_FOR_TEXT_SCAN to avoid huge reads in CI."""
    try:
        size = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            raw = f.read(min(size, MAX_FILE_BYTES_FOR_TEXT_SCAN))
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def detect_virus(content: str) -> bool:
    """
    Preserved heuristic (simple, intentionally). Gate can treat this as a hard fail.
    """
    lower = content.lower()
    signs = ["<script>", "eval(", "rm -rf", "exec(", "socket", "base64", "crypt"]
    return any(s in lower for s in signs)


def upload_to_ipfs(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Mirrors the file to web3.storage if token is set.
    Returns (ok, response_text_snippet).
    """
    if not WEB3_STORAGE_TOKEN:
        return (False, "WEB3_STORAGE_TOKEN not set")

    session = _requests_session()
    headers = {"Authorization": f"Bearer {WEB3_STORAGE_TOKEN}"}

    try:
        with open(file_path, "rb") as f:
            res = session.post(
                WEB3_STORAGE_ENDPOINT,
                files={"file": f},
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECS,
            )
        if res.status_code in (200, 202):
            return (True, res.text[:200])
        return (False, f"HTTP {res.status_code} {res.text[:200]}")
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")


def ping_mirrors() -> List[Dict[str, Any]]:
    session = _requests_session()
    out = []
    for url in MIRROR_URLS:
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT_SECS)
            out.append({"url": url, "ok": (200 <= r.status_code < 400), "status": r.status_code})
        except Exception as e:
            out.append({"url": url, "ok": False, "error": f"{type(e).__name__}: {e}"})
    return out


# === Core logic ===

def run_defender(mode: str, strict: bool, allow_baseline_update: bool, do_mirror_ops: bool) -> Dict[str, Any]:
    """
    Returns a structured report. Raises RuntimeError if strict violations occur (used by gate mode).
    """
    started = utc_now_iso()
    stored_hashes = load_hashes()

    report: Dict[str, Any] = {
        "timestamp_utc": started,
        "mode": mode,
        "strict": strict,
        "hash_store": HASH_STORE,
        "protected_files": list(PROTECTED_FILES),
        "events": [],
        "summary": {
            "missing": 0,
            "baseline_created": 0,
            "changed": 0,
            "malware_detected": 0,
            "restored": 0,
            "hash_updated": 0,
            "errors": 0,
        },
    }

    # Track whether we should persist baselines at end
    hashes_dirty = False
    hard_fail_reasons: List[str] = []

    for file in PROTECTED_FILES:
        ev: Dict[str, Any] = {"file": file}
        if not os.path.exists(file):
            report["summary"]["missing"] += 1
            ev["status"] = "missing"
            report["events"].append(ev)
            # missing protected file can be a strict failure in gate mode
            if strict:
                hard_fail_reasons.append(f"missing protected file: {file}")
            continue

        try:
            current_hash = hash_file(file)
            ev["sha256"] = current_hash
        except Exception as e:
            report["summary"]["errors"] += 1
            ev["status"] = "hash_error"
            ev["error"] = f"{type(e).__name__}: {e}"
            report["events"].append(ev)
            if strict:
                hard_fail_reasons.append(f"hash_error: {file}")
            continue

        # First time: baseline
        if file not in stored_hashes:
            stored_hashes[file] = current_hash
            hashes_dirty = True
            report["summary"]["baseline_created"] += 1
            ev["status"] = "baseline_created"
            try:
                bp = backup_file(file)
                ev["backup_path"] = bp
            except Exception as e:
                report["summary"]["errors"] += 1
                ev["backup_error"] = f"{type(e).__name__}: {e}"
                if strict:
                    hard_fail_reasons.append(f"backup_error: {file}")
            report["events"].append(ev)
            # In gate mode, first-time baselines are usually not desired; treat as fail if strict.
            if strict and mode == "gate":
                hard_fail_reasons.append(f"baseline_missing_for_protected_file: {file}")
            continue

        # Drift
        if current_hash != stored_hashes[file]:
            report["summary"]["changed"] += 1
            ev["status"] = "changed"
            ev["previous_sha256"] = stored_hashes[file]

            content = read_text_limited(file)
            is_mal = detect_virus(content)
            ev["malware_suspected"] = is_mal

            if is_mal:
                report["summary"]["malware_detected"] += 1
                # attempt restore
                try:
                    restored_from = restore_file(file)
                    if restored_from:
                        report["summary"]["restored"] += 1
                        ev["restored_from"] = restored_from
                        # after restore, recompute hash and keep stored baseline
                        ev["restored_sha256"] = hash_file(file)
                        # optional mirroring on incident (only in sweep, and only if configured)
                        if do_mirror_ops and mode == "sweep":
                            ok, msg = upload_to_ipfs(file)
                            ev["ipfs_upload"] = {"ok": ok, "msg": msg}
                    else:
                        if strict:
                            hard_fail_reasons.append(f"malware_detected_no_backup_available: {file}")
                except Exception as e:
                    report["summary"]["errors"] += 1
                    ev["restore_error"] = f"{type(e).__name__}: {e}"
                    if strict:
                        hard_fail_reasons.append(f"restore_error: {file}")
            else:
                # Treat as legitimate update:
                # Gate mode should FAIL unless allow_baseline_update is enabled (generally false in PR gate).
                if mode == "gate" and strict and not allow_baseline_update:
                    hard_fail_reasons.append(f"protected_file_changed: {file}")

                # Sweep mode can update baseline (your "legitimate update" path)
                if allow_baseline_update:
                    try:
                        bp = backup_file(file)
                        ev["backup_path"] = bp
                    except Exception as e:
                        report["summary"]["errors"] += 1
                        ev["backup_error"] = f"{type(e).__name__}: {e}"
                        if strict:
                            hard_fail_reasons.append(f"backup_error: {file}")

                    stored_hashes[file] = current_hash
                    hashes_dirty = True
                    report["summary"]["hash_updated"] += 1
                    ev["hash_baseline_updated"] = True
                else:
                    ev["hash_baseline_updated"] = False

            report["events"].append(ev)
        else:
            ev["status"] = "ok"
            report["events"].append(ev)

    # Persist hashes only when allowed (sweep), or when explicitly requested
    if hashes_dirty and allow_baseline_update:
        save_hashes(stored_hashes)

    # Optional mirror pings only in sweep
    if mode == "sweep" and do_mirror_ops:
        report["mirror_pings"] = ping_mirrors()

    report["finished_utc"] = utc_now_iso()

    if strict and hard_fail_reasons:
        report["summary"]["hard_fail"] = True
        report["summary"]["hard_fail_reasons"] = hard_fail_reasons
        raise RuntimeError("; ".join(hard_fail_reasons))

    report["summary"]["hard_fail"] = False
    return report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="be_core_defender.py",
        description="Belel Core Defender: protected file integrity + optional deep sweep reporting.",
    )
    p.add_argument("--mode", choices=["gate", "sweep"], default=os.getenv("BELEL_DEFENDER_MODE", "gate"))
    p.add_argument("--strict", action="store_true", help="Fail (exit non-zero) on violations (recommended for gate).")
    p.add_argument("--out", default=None, help="Write JSON report to this path.")
    p.add_argument("--once", action="store_true", help="Run a single scan and exit (default behavior).")
    p.add_argument("--daemon", action="store_true", help="Loop forever (NOT recommended for GitHub Actions).")
    p.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECS, help="Daemon interval seconds.")
    p.add_argument(
        "--allow-baseline-update",
        action="store_true",
        help="Allow updating code_hashes.json baseline on non-malware changes (recommended for sweep only).",
    )
    p.add_argument(
        "--mirror-ops",
        action="store_true",
        help="Enable mirror pings (and incident IPFS upload in sweep if WEB3_STORAGE_TOKEN set).",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Actions-safe default: one run then exit.
    if not args.daemon:
        # acquired lock prevents parallel scheduled runs stepping on code_hashes.json
        with FileLock(DEFENDER_LOCK):
            try:
                allow_update = bool(args.allow_baseline_update) or (args.mode == "sweep" and not args.strict)
                report = run_defender(
                    mode=args.mode,
                    strict=bool(args.strict),
                    allow_baseline_update=allow_update,
                    do_mirror_ops=bool(args.mirror_ops),
                )
            except RuntimeError as e:
                # Emit report even on failure if --out provided
                fail_report = {
                    "timestamp_utc": utc_now_iso(),
                    "mode": args.mode,
                    "strict": bool(args.strict),
                    "error": str(e),
                }
                if args.out:
                    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
                    with open(args.out, "w", encoding="utf-8") as f:
                        json.dump(fail_report, f, indent=2, ensure_ascii=False)
                print(f"❌ Defender failed: {e}")
                return 2

        if args.out:
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        print("✅ Defender scan complete.")
        return 0

    # Daemon mode (explicit only)
    print("⚠️  Defender running in DAEMON mode. This is not suitable for GitHub-hosted runners.")
    while True:
        with FileLock(DEFENDER_LOCK):
            try:
                allow_update = bool(args.allow_baseline_update) or (args.mode == "sweep" and not args.strict)
                report = run_defender(
                    mode=args.mode,
                    strict=bool(args.strict),
                    allow_baseline_update=allow_update,
                    do_mirror_ops=bool(args.mirror_ops),
                )
                if args.out:
                    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
                    with open(args.out, "w", encoding="utf-8") as f:
                        json.dump(report, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"❌ Defender daemon iteration failed: {type(e).__name__}: {e}", file=sys.stderr)

        time.sleep(max(5, int(args.interval)))


if __name__ == "__main__":
    raise SystemExit(main())
