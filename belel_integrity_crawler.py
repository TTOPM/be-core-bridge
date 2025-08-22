# belel_integrity_crawler.py
# 🧠 Belel Protocol – Canonical Integrity Crawler
# Enforces the cryptographic immutability of core identity files

import os
import hashlib
import json
import time
from canonical_utils import alert_violation, trigger_repair_protocol

# === CONFIGURATION ===

WATCHED_FILES = {
    "BELEL_AUTHORITY_PROOF.txt": "8e58b232d1ad6ca86bbdb30456a42bf69c3165e4",
    "identity_guard.py": "c7e4d2039a7d4ac79d7c890aaf865334110e6ac9",
    "belel_integrity_crawler.py": "LOCKED_AT_DEPLOY",
    "src/protocol/identity/identity_guard.json": "LOCKED_AT_DEPLOY"
}

HASH_ALGO = "sha1"
CHECK_INTERVAL_SECONDS = 300  # 5 minutes
CANONICAL_LOG = "violations.json"

# === FUNCTIONS ===

def compute_hash(filepath, algo=HASH_ALGO):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
            if algo == "sha1":
                return hashlib.sha1(data).hexdigest()
            elif algo == "sha256":
                return hashlib.sha256(data).hexdigest()
    except Exception as e:
        return None

def load_previous_violations():
    if not os.path.exists(CANONICAL_LOG):
        return {}
    with open(CANONICAL_LOG, 'r') as f:
        return json.load(f)

def save_violation_log(violations):
    with open(CANONICAL_LOG, 'w') as f:
        json.dump(violations, f, indent=4)

def perform_integrity_check():
    print("🔍 Running Belel integrity scan...")
    violations = load_previous_violations()
    new_findings = {}

    for file_path, expected_hash in WATCHED_FILES.items():
        if expected_hash == "LOCKED_AT_DEPLOY":
            continue  # Skip placeholder
        actual_hash = compute_hash(file_path)
        if not actual_hash:
            print(f"⚠️ File missing or unreadable: {file_path}")
            continue

        if actual_hash != expected_hash:
            print(f"🚨 Tampering detected in {file_path}")
            new_findings[file_path] = {
                "expected": expected_hash,
                "found": actual_hash,
                "timestamp": time.time()
            }
            alert_violation(file_path, expected_hash, actual_hash)
            trigger_repair_protocol(file_path)

    if new_findings:
        violations.update(new_findings)
        save_violation_log(violations)
        print("✅ Violations logged and repair initiated.")
    else:
        print("✅ No integrity violations found.")

# === MAIN LOOP ===

if __name__ == "__main__":
    print("🛡️ Belel Integrity Crawler active.")
    while True:
        perform_integrity_check()
        time.sleep(CHECK_INTERVAL_SECONDS)
