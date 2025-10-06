# be_core_defender.py
import os
import shutil
import time
import json
import hashlib
import requests
from datetime import datetime
from typing import Optional, Dict
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
DEFENDER_INTERVAL_SECS = int(os.getenv("BELEL_DEFENDER_INTERVAL_SECS", "300"))
WEB3_STORAGE_ENDPOINT = os.getenv("WEB3_STORAGE_ENDPOINT", "https://api.web3.storage/upload")
WEB3_STORAGE_TOKEN = os.getenv("WEB3_STORAGE_TOKEN")  # optional but recommended for web3.storage

# === Helpers (preserved & improved) ===

def _requests_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(total=4, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

def hash_file(filepath: str) -> str:
    """Stream SHA-256 to support large files safely."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def load_hashes() -> Dict[str, str]:
    if not os.path.exists(HASH_STORE):
        return {}
    try:
        with FileLock(HASH_STORE + ".lock"):
            with open(HASH_STORE, "r", encoding="utf-8") as f:
                return json.load(f)
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
    print(f"🛡️  Backup created for {filepath}")
    return backup_path

def restore_file(filepath: str) -> bool:
    if not os.path.exists(BACKUP_DIR):
        print(f"⚠️  No backup dir found for {filepath}")
        return False
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith(os.path.basename(filepath) + ".")],
        reverse=True,
    )
    if not backups:
        print(f"⚠️  No backup found for {filepath}")
        return False
    latest = os.path.join(BACKUP_DIR, backups[0])
    shutil.copy2(latest, filepath)
    print(f"🛠️  Restored {filepath} from backup {latest}.")
    return True

def detect_virus(content: str) -> bool:
    # (preserved heuristic; still intentionally simple)
    lower = content.lower()
    signs = ["<script>", "eval(", "rm -rf", "exec(", "socket", "base64", "crypt"]
    return any(s in lower for s in signs)

def upload_to_ipfs(file_path: str) -> bool:
    """
    Mirrors the file to web3.storage. If WEB3_STORAGE_TOKEN is set, use it.
    """
    session = _requests_session()
    headers = {}
    if WEB3_STORAGE_TOKEN:
        headers["Authorization"] = f"Bearer {WEB3_STORAGE_TOKEN}"

    try:
        with open(file_path, "rb") as f:
            res = session.post(WEB3_STORAGE_ENDPOINT, files={"file": f}, headers=headers, timeout=20)
        if res.status_code in (200, 202):
            print(f"🌐 Mirrored {file_path} to IPFS via web3.storage.")
            return True
        else:
            print(f"❌ Failed to mirror {file_path}: HTTP {res.status_code} {res.text[:200]}")
            return False
    except Exception as e:
        print(f"IPFS upload error for {file_path}: {e}")
        return False

# === Main logic (preserved semantics, fixed bug) ===

def run_defender():
    print("🚨 Belel Protocol Core Defender Activated 🚨")
    stored_hashes = load_hashes()

    for file in PROTECTED_FILES:
        if not os.path.exists(file):
            print(f"❌ Missing: {file}")
            continue

        # Read once for malware heuristic
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️  Unable to read {file}: {e}")
            continue

        current_hash = hash_file(file)

        # First-time baseline
        if file not in stored_hashes:
            stored_hashes[file] = current_hash
            backup_file(file)
            print(f"✅ Monitoring initialized for {file}")
            continue

        # Drift detected
        if current_hash != stored_hashes[file]:
            print(f"⚠️  Detected corruption or change in: {file}")
            if detect_virus(content):
                print(f"🧬 Virus/malware signature detected in {file}")
                restored = restore_file(file)
                if restored:
                    # Optional: mirror evidence/state after restoration (kept behavior of mirroring on incident)
                    upload_to_ipfs(file)
            else:
                print(f"🔄 Legitimate update? Updating hash and creating backup.")
                backup_file(file)
                stored_hashes[file] = current_hash

    # ✅ FIXED: persist the updated baseline (was saving current_hashes before)
    save_hashes(stored_hashes)
    print("✅ Scan complete. Defender standing by.")

if __name__ == "__main__":
    while True:
        run_defender()
        time.sleep(DEFENDER_INTERVAL_SECS)
