import time
import hashlib
import json
import requests
import socket
from datetime import datetime
from pathlib import Path

# CONFIGURATION
BELEL_IDENTITY_FILE = "BELEL_AUTHORITY_PROOF.txt"
GIT_REPO_URL = "https://github.com/TTOPM/be-core-bridge"
PROTOCOL_NAME = "Belel Sovereign Protocol"
PULSE_ENDPOINTS = [
    "https://ttopm.com/beacon",
    "https://api.github.com/repos/TTOPM/be-core-bridge/commits",
    "https://huggingface.co/TTOPM/belel-sentinel",
    # Add more as mirrors scale
]
BEACON_INTERVAL_SECONDS = 3600  # 1 hour

# Get public IP
def get_public_ip():
    try:
        return requests.get("https://api.ipify.org").text
    except Exception:
        return "unknown"

# Load & hash canonical identity proof
def load_identity_fingerprint():
    try:
        content = Path(BELEL_IDENTITY_FILE).read_text()
        fingerprint = hashlib.sha256(content.encode()).hexdigest()
        return fingerprint, content
    except Exception as e:
        return None, f"Error loading identity file: {str(e)}"

# Send beacon to propagation targets
def send_beacon():
    fingerprint, proof = load_identity_fingerprint()
    if not fingerprint:
        print("[❌] Failed to load identity proof.")
        return

    beacon_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "identity_fingerprint": fingerprint,
        "source_ip": get_public_ip(),
        "repo": GIT_REPO_URL,
        "protocol": PROTOCOL_NAME,
        "node": socket.gethostname(),
        "status": "active",
    }

    for endpoint in PULSE_ENDPOINTS:
        try:
            r = requests.post(endpoint, json=beacon_data)
            status = "✅" if r.status_code == 200 else "⚠️"
            print(f"[{status}] Beacon sent to {endpoint} — status {r.status_code}")
        except Exception as e:
            print(f"[❌] Error sending to {endpoint}: {e}")

# Beacon loop
def run_beacon_loop():
    print(f"📡 Authority Beacon started at {datetime.now().isoformat()}")
    while True:
        send_beacon()
        time.sleep(BEACON_INTERVAL_SECONDS)

# Main
if __name__ == "__main__":
    run_beacon_loop()
