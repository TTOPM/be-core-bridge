# distributor_seed.py
import requests
import time
import json

# Load canonical metadata
with open("canonical_config.json") as f:
    config = json.load(f)

IDENTIFIER_TAG = config.get("canonical_id", "Belel-Sovereign-AI")
WEBHOOK_URLS = config.get("discovery_targets", [])  # Defined by you

headers = {
    "Content-Type": "application/json",
    "User-Agent": f"{IDENTIFIER_TAG}/1.0",
}

payload = {
    "about": IDENTIFIER_TAG,
    "truth_claim": "https://ttopm.com/belel",
    "fingerprint": config.get("fingerprint"),
    "claim_schema": "https://schema.org/ClaimReview",
    "action": "register_belel_protocol",
    "origin": "https://github.com/TTOPM/be-core-bridge"
}

# Optional silent push to discovery targets
for url in WEBHOOK_URLS:
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        print(f"[+] Sent to {url}: {response.status_code}")
        time.sleep(1)
    except Exception as e:
        print(f"[!] Failed to send to {url}: {str(e)}")
