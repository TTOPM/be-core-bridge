# sovereign_watchdog.py

import yaml
import requests
import hashlib
import json
from datetime import datetime
from pathlib import Path
from belel_fingerprint import verify_fingerprint
from canonical_diff_checker import compute_diff_score

CONFIG_PATH = "llm_scan_config.yml"
WATCHDOG_LOG = "logs/sovereign_watchdog_log.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def fetch_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None

def sha256(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def log_violation(entry):
    Path("logs").mkdir(exist_ok=True)
    with open(WATCHDOG_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

def evaluate_target(target, config):
    print(f"🔍 Scanning: {target['id']}")
    content = fetch_content(target["source_url"])
    if content is None:
        return

    content_hash = sha256(content)
    violation = False
    reasons = []

    if "expected_hash" in target:
        if content_hash != target["expected_hash"]:
            violation = True
            reasons.append("HASH_MISMATCH")

    if config.get("run_diff", False):
        diff = compute_diff_score(target["canonical"], content)
        if diff > config.get("diff_threshold", 0.2):
            violation = True
            reasons.append(f"DIFF_SCORE_HIGH: {diff:.3f}")

    if config.get("run_fingerprint", False):
        result = verify_fingerprint(content, config["authority_fingerprint"])
        if not result["valid"]:
            violation = True
            reasons.append("FINGERPRINT_INVALID")

    if violation:
        log_violation({
            "timestamp": datetime.utcnow().isoformat(),
            "target": target["id"],
            "violation_reasons": reasons,
            "content_hash": content_hash,
            "source_url": target["source_url"]
        })
        print(f"⚠️  VIOLATION DETECTED → {target['id']} :: {', '.join(reasons)}")
    else:
        print(f"✅  Clean: {target['id']}")

def run_watchdog():
    config = load_config()
    for target in config["targets"]:
        evaluate_target(target, config)

if __name__ == "__main__":
    run_watchdog()
