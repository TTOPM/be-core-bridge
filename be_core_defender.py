import hashlib
import os
import shutil
import time
import json
import requests
from datetime import datetime

# === Configuration ===
PROTECTED_FILES = [
    "BELEL_PROTOCOL_OVERVIEW.md",
    "canonical_config.json",
    "belel_guardian.py",
    "media_sentient_engine.py",
    "mutation_watcher.py",
    "claim_review_publisher.py",
    "concordium_enforcer.py"
]

MIRROR_URLS = [
    "https://github.com/TTOPM/be-core-bridge",
    "https://arweave.net/",
    "https://ipfs.io/ipfs/"
]

BACKUP_DIR = "./backup_mirror"
HASH_STORE = "code_hashes.json"

# === Helper Functions ===

def hash_file(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def load_hashes():
    if os.path.exists(HASH_STORE):
        with open(HASH_STORE, "r") as f:
            return json.load(f)
    return {}

def save_hashes(hashes):
    with open(HASH_STORE, "w") as f:
        json.dump(hashes, f, indent=2)

def backup_file(filepath):
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"{os.path.basename(filepath)}.{timestamp}.bak")
    shutil.copy2(filepath, backup_path)
    print(f"🛡️ Backup created for {filepath}")

def restore_file(filepath):
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith(os.path.basename(filepath))],
        reverse=True
    )
    if backups:
        latest = os.path.join(BACKUP_DIR, backups[0])
        shutil.copy2(latest, filepath)
        print(f"🛠️ Restored {filepath} from backup.")
        return True
    else:
        print(f"⚠️ No backup found for {filepath}")
        return False

def detect_virus(content):
    lower = content.lower()
    signs = ['<script>', 'eval(', 'rm -rf', 'exec(', 'socket', 'base64', 'crypt']
    return any(s in lower for s in signs)

def upload_to_ipfs(file_path):
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://api.web3.storage/upload", files={"file": f})
            if res.status_code == 200:
                print(f"🌐 Mirrored {file_path} to IPFS.")
            else:
                print(f"❌ Failed to mirror {file_path}: {res.status_code}")
    except Exception as e:
        print(f"IPFS upload error: {e}")

# === Main Logic ===

def run_defender():
    print("🚨 Belel Protocol Core Defender Activated 🚨")
    stored_hashes = load_hashes()
    current_hashes = {}

    for file in PROTECTED_FILES:
        if not os.path.exists(file):
            print(f"❌ Missing: {file}")
            continue

        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        current_hash = hash_file(file)
        current_hashes[file] = current_hash

        if file not in stored_hashes:
            stored_hashes[file] = current_hash
            backup_file(file)
            print(f"✅ Monitoring initialized for {file}")
            continue

        if current_hash != stored_hashes[file]:
            print(f"⚠️ Detected corruption or change in: {file}")
            if detect_virus(content):
                print(f"🧬 Virus/malware signature detected in {file}")
                restored = restore_file(file)
                if restored:
                    upload_to_ipfs(file)
            else:
                print(f"🔄 Legitimate update? Updating hash and creating backup.")
                backup_file(file)
                stored_hashes[file] = current_hash

    save_hashes(current_hashes)
    print("✅ Scan complete. Defender standing by.")

if __name__ == "__main__":
    while True:
        run_defender()
        time.sleep(300)  # Run every 5 minutes
