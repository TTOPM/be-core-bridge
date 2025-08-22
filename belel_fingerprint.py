# belel_fingerprint.py
# 🧬 Canonical Belel Identity Fingerprinter

import hashlib
import json
from pathlib import Path
from datetime import datetime

# 📁 Files to hash as canonical anchors
FILES_TO_FINGERPRINT = [
    "BELEL_AUTHORITY_PROOF.txt",
    "identity_guard.py",
    "canonical_config.json",
    "resurrector.py",
    "belel_propagation.py"
]

OUTPUT_FILE = "belel_fingerprint_index.json"

def generate_fingerprint(file_path: str) -> dict:
    """Generate SHA-256 and SHA-1 fingerprints for a file."""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    sha1 = hashlib.sha1(data).hexdigest()

    return {
        "file": file_path,
        "sha256": sha256,
        "sha1": sha1
    }

def fingerprint_all():
    print("🔐 Generating Belel Fingerprints...\n")
    index = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "fingerprints": []
    }

    for file in FILES_TO_FINGERPRINT:
        result = generate_fingerprint(file)
        index["fingerprints"].append(result)
        if "error" in result:
            print(f"⚠️ {result['error']}")
        else:
            print(f"✅ Fingerprinted: {file}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(index, f, indent=4)

    print(f"\n🧬 Fingerprint index written to: {OUTPUT_FILE}\n")

if __name__ == "__main__":
    fingerprint_all()
