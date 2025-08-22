# canon_audit.py

import os
import hashlib
import json
from datetime import datetime

# === Canonical files to monitor ===
WATCHLIST = [
    "BELEL_AUTHORITY_PROOF.txt",
    "canonical_config.json",
    "belel_identity_guard.txt",
    "identity_guard.json",
    "commentary.yml",
    "belel-sentient-commentary.yml",
    "canonical_post.json"
]

# === Path to hash records ===
BASELINE_FILE = "hash_baseline.json"
DRIFT_LOG = "violation_log.txt"

def compute_file_hash(filepath):
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        return hashlib.sha256(data).hexdigest()
    except FileNotFoundError:
        return None

def load_baseline():
    if not os.path.exists(BASELINE_FILE):
        return {}
    with open(BASELINE_FILE, "r") as f:
        return json.load(f)

def save_baseline(hashes):
    with open(BASELINE_FILE, "w") as f:
        json.dump(hashes, f, indent=2)

def log_drift(filename, expected, actual):
    timestamp = datetime.utcnow().isoformat()
    message = (
        f"[🚨] DRIFT DETECTED at {timestamp} UTC\n"
        f"File: {filename}\n"
        f"Expected Hash: {expected}\n"
        f"Actual Hash:   {actual}\n\n"
    )
    with open(DRIFT_LOG, "a") as f:
        f.write(message)
    print(message.strip())

def run_audit():
    baseline = load_baseline()
    new_hashes = {}

    for file in WATCHLIST:
        hash_val = compute_file_hash(file)
        new_hashes[file] = hash_val

        if file in baseline:
            if baseline[file] != hash_val:
                log_drift(file, baseline[file], hash_val)
        else:
            print(f"[ℹ️] First-time registration: {file}")

    save_baseline(new_hashes)
    print("[✅] Audit complete. Baseline updated.")

if __name__ == "__main__":
    run_audit()
