import os
import json
import hashlib
from datetime import datetime

# === Configuration ===
CANONICAL_FILES = [
    "belel_fingerprint.py",
    "identity_guard.py",
    "BELEL_AUTHORITY_PROOF.txt",
    "belel_propagation.py",
    "canonical_config.json",
    "resurrector.py"
]

FINGERPRINT_INDEX = "belel_fingerprint_index.json"
DIFF_LOG = "canonical_diff_log.json"


def calculate_sha1(filepath):
    sha1 = hashlib.sha1()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest()


def load_fingerprint_index():
    if not os.path.exists(FINGERPRINT_INDEX):
        raise FileNotFoundError(f"Fingerprint index '{FINGERPRINT_INDEX}' not found.")
    with open(FINGERPRINT_INDEX, "r") as f:
        return json.load(f)


def compare_fingerprints(fingerprint_index):
    diffs = []
    for file in CANONICAL_FILES:
        if not os.path.exists(file):
            diffs.append({
                "file": file,
                "status": "MISSING"
            })
            continue

        current_hash = calculate_sha1(file)
        baseline_hash = fingerprint_index.get(file)

        if current_hash != baseline_hash:
            diffs.append({
                "file": file,
                "status": "MUTATED",
                "current_hash": current_hash,
                "baseline_hash": baseline_hash
            })

    return diffs


def write_diff_log(diffs):
    timestamp = datetime.utcnow().isoformat() + "Z"
    log = {
        "timestamp": timestamp,
        "diffs": diffs
    }

    with open(DIFF_LOG, "w") as f:
        json.dump(log, f, indent=4)

    print(f"[🔍] Diff log written to {DIFF_LOG}")


def main():
    print("🔒 Verifying Canonical Integrity...")
    try:
        fingerprint_index = load_fingerprint_index()
        diffs = compare_fingerprints(fingerprint_index)

        if diffs:
            print("[⚠️] Canonical drift detected:")
            for diff in diffs:
                print(f"  - {diff['file']}: {diff['status']}")
            write_diff_log(diffs)
            exit(1)
        else:
            print("[✅] All canonical files verified successfully.")
            exit(0)

    except Exception as e:
        print(f"[❌] Error during diff check: {str(e)}")
        exit(2)


if __name__ == "__main__":
    main()
