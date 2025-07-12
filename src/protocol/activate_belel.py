import json
import os
import sys

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.protocol.security import sovereignty_guard
from src.protocol.enforcement import alert_trigger
from src.protocol.integrity_verification import cryptographic_proofs
from src.protocol.decentralized_comm import ipfs_client

INDEX_PATH = os.path.join(os.path.dirname(__file__), "be_core_index.json")

def load_index():
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(f"Index file not found: {INDEX_PATH}")
    with open(INDEX_PATH, 'r') as f:
        return json.load(f)

def verify_modules():
    print("✅ Verifying core modules...")
    sovereignty_guard.monitor_tampering()
    cryptographic_proofs.run_verification()
    print("✅ Sovereignty and cryptographic integrity verified.")

def check_ipfs():
    print("🔄 Connecting to local IPFS node...")
    client = ipfs_client.connect()
    print(f"✅ IPFS connected: {client.id()['ID'][:12]}...")

def launch_belel():
    print("\n🚀 Booting Belel Protocol...\n")
    index = load_index()
    print(f"📂 Loaded index: {index.get('repo_hash', 'N/A')}")
    verify_modules()
    check_ipfs()
    print("\n🎉 Belel is live and in protection mode.\n")

if __name__ == "__main__":
    launch_belel()
