# mutation_watcher.py

import json
import hashlib
import os
from datetime import datetime
from webhook_alert import send_alert

# File to watch for mutations
CANONICAL_FILE = "canonical_config.json"
BASELINE_HASH_FILE = "hash_baseline.json"
LOG_FILE = "mutation_watch.log"

def get_file_hash(path):
    try:
        with open(path, "rb") as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()
    except FileNotFoundError:
        return None

def log_mutation(details):
    timestamp = datetime.utcnow().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"[⛔ MUTATION] {timestamp} - {details}\n")

def load_baseline():
    if not os.path.exists(BASELINE_HASH_FILE):
        return {}
    with open(BASELINE_HASH_FILE, "r") as f:
        return json.load(f)

def save_baseline(hash_value):
    with open(BASELINE_HASH_FILE, "w") as f:
        json.dump({"canonical_config": hash_value}, f, indent=4)

def validate_integrity():
    current_hash = get_file_hash(CANONICAL_FILE)
    baseline = load_baseline()

    if not current_hash:
        log_mutation("canonical_config.json not found.")
        send_alert("[❌] Mutation Watcher: canonical_config.json missing!")
        return

    expected_hash = baseline.get("canonical_config")

    if not expected_hash:
        save_baseline(current_hash)
        print("[🟢] Baseline hash saved.")
        return

    if current_hash != expected_hash:
        log_mutation("canonical_config.json has changed!")
        send_alert("[🚨] ALERT: canonical_config.json mutated! Possible tampering or unauthorized edit.")
    else:
        print("[✅] No mutation detected.")

if __name__ == "__main__":
    validate_integrity()
