#!/usr/bin/env python3
"""
update_blocklist.py
Belel Shield – Manual Blocklist Updater (with SHA-256 verification)
Downloads belel-blocklist.json + belel-blocklist.checksums.json,
verifies integrity, then updates ~/.belel/belel-blocklist.json.
"""

import urllib.request, json, hashlib
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/TTOPM/be-core-bridge/main/belel-shield/sentinel/blocklists"
BLOCKLIST_URL = f"{BASE_URL}/belel-blocklist.json"
CHECKSUM_URL  = f"{BASE_URL}/belel-blocklist.checksums.json"

DATA_DIR = Path.home() / ".belel"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = DATA_DIR / "belel-blocklist.json"
TMP_FILE   = DATA_DIR / "belel-blocklist.tmp"
CHECK_FILE = DATA_DIR / "belel-blocklist.checksums.json"
LOG_FILE   = DATA_DIR / "update.log"

def _log(msg: str):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def update_blocklist():
    try:
        _log(f"[*] Fetching checksum: {CHECKSUM_URL}")
        urllib.request.urlretrieve(CHECKSUM_URL, CHECK_FILE)
        meta = json.loads(CHECK_FILE.read_text())

        expected_algo = meta.get("algo")
        expected_hash = meta.get("hash")
        artifact      = meta.get("artifact", "belel-blocklist.json")

        if expected_algo != "sha256" or not expected_hash:
            _log("[!] Invalid checksum file (missing algo/hash). Aborting.")
            return

        _log(f"[*] Fetching blocklist: {BLOCKLIST_URL}")
        urllib.request.urlretrieve(BLOCKLIST_URL, TMP_FILE)

        actual_hash = _sha256(TMP_FILE)
        if actual_hash.lower() != expected_hash.lower():
            _log(f"[!] HASH MISMATCH for {artifact}: expected {expected_hash}, got {actual_hash}. Aborting update.")
            TMP_FILE.unlink(missing_ok=True)
            return

        TMP_FILE.replace(CACHE_FILE)
        data = json.loads(CACHE_FILE.read_text())
        _log(f"[+] Blocklist verified & updated: {len(data.get('ip_ranges', []))} IP ranges, {len(data.get('domains', []))} domains")

    except Exception as e:
        _log(f"[!] Blocklist update failed: {e}")

if __name__ == "__main__":
    update_blocklist()
