#!/usr/bin/env python3
"""
update_blocklist.py
Belel Shield – Manual Blocklist Updater

Fetches the latest belel-blocklist.json from GitHub/IPFS and saves it locally.
Intended for citizens who want to refresh their blocklist on demand.
"""

import urllib.request
import json
from pathlib import Path

# === CONFIG ===
BLOCKLIST_URL = "https://raw.githubusercontent.com/YOUR_GITHUB/belel-shield/main/sentinel/blocklists/belel-blocklist.json"

DATA_DIR = Path.home() / ".belel"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = DATA_DIR / "belel-blocklist.json"

def update_blocklist():
    try:
        print(f"[*] Fetching latest blocklist from {BLOCKLIST_URL} ...")
        urllib.request.urlretrieve(BLOCKLIST_URL, CACHE_FILE)
        data = json.loads(CACHE_FILE.read_text())
        print(f"[+] Blocklist updated: {len(data.get('ip_ranges', []))} IP ranges, {len(data.get('domains', []))} domains")
    except Exception as e:
        print(f"[!] Blocklist update failed: {e}")

if __name__ == "__main__":
    update_blocklist()
