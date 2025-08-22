# resurrector.py
# 🧬 Belel Protocol Resurrection Layer

import os
import hashlib
import json
import requests
from canonical_utils import alert_violation

# 📁 Files to verify + their reference hashes (shortened example for demo)
REFERENCE_HASHES = {
    "BELEL_AUTHORITY_PROOF.txt": "8e58b232d1ad6ca86bbdb30456a42bf69c3165e4",
    "identity_guard.py": "4a36ae59e310cbb4dcaa2b911fcd834a2bc713bb",
    "sovereignty_guard.py": "3b9f90fe54c6b5a6f8f5b9c72c73466cb86a0b97"
}

MIRROR_SOURCES = [
    "https://raw.githubusercontent.com/TTOPM/be-core-bridge/main/",
    "https://ipfs.io/ipfs/QmBelelMirrorFiles/",  # Replace with actual CID
    "https://arweave.net/BelelArchive/"
]

def sha1_of_file(filename):
    sha1 = hashlib.sha1()
    try:
        with open(filename, 'rb') as f:
            while chunk := f.read(8192):
                sha1.update(chunk)
        return sha1.hexdigest()
    except FileNotFoundError:
        return None

def resurrect_file(file):
    print(f"⚠️ Attempting to resurrect: {file}")
    for source in MIRROR_SOURCES:
        try:
            url = source + file
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(file, "wb") as f:
                    f.write(r.content)
                print(f"✅ Resurrected {file} from {source}")
                return True
        except Exception as e:
            print(f"❌ Failed from {source}: {e}")
    alert_violation("Resurrection Failure", file, "Could not restore from any mirror")
    return False

def scan_and_resurrect():
    print("🧬 Scanning for corruption or deletion...")
    for file, expected_hash in REFERENCE_HASHES.items():
        actual_hash = sha1_of_file(file)
        if not actual_hash:
            print(f"🚨 File missing: {file}")
            resurrect_file(file)
        elif actual_hash != expected_hash:
            print(f"🧨 File tampered: {file}")
            alert_violation("File tampered", file, f"Expected {expected_hash}, got {actual_hash}")
            resurrect_file(file)
        else:
            print(f"✔️ {file} verified clean.")

if __name__ == "__main__":
    scan_and_resurrect()
