# trust_score_audit.py

import yaml
import hashlib
import json
from datetime import datetime
from canonical_diff_checker import compute_diff_score
from belel_fingerprint import verify_fingerprint
from pathlib import Path

TRUST_LOG_PATH = "logs/trustscore_log.json"
POLICY_FILE = "trustscore.yml"

def load_policy():
    with open(POLICY_FILE, "r") as f:
        return yaml.safe_load(f)

def log_score(target_id, trust_score, metadata):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "target_id": target_id,
        "trust_score": trust_score,
        "metadata": metadata
    }
    Path("logs").mkdir(exist_ok=True)
    with open(TRUST_LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def score_fingerprint(fingerprint_result):
    return 1.0 if fingerprint_result["valid"] else 0.0

def score_diff(diff_score):
    if diff_score == 0:
        return 1.0
    elif diff_score < 0.1:
        return 0.8
    elif diff_score < 0.3:
        return 0.5
    else:
        return 0.0

def compute_trust_score(target, policy):
    diff_score = compute_diff_score(target["canonical_file"], target["observed_file"])
    fingerprint_result = verify_fingerprint(target["observed_file"], policy["authority_fingerprint"])

    final_score = (
        policy["weights"]["fingerprint"] * score_fingerprint(fingerprint_result)
        + policy["weights"]["diff"] * score_diff(diff_score)
    )

    log_score(target["id"], final_score, {
        "diff_score": diff_score,
        "fingerprint_valid": fingerprint_result["valid"]
    })

    return final_score

if __name__ == "__main__":
    policy = load_policy()
    targets = policy["targets"]

    print(f"🔎 Running Trust Score Audit on {len(targets)} targets...")
    for t in targets:
        score = compute_trust_score(t, policy)
        print(f"→ {t['id']} :: TRUST SCORE = {score:.2f}")
