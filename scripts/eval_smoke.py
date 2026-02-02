from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

BASELINE_PATH = Path("metrics/eval_baseline.json")
LATEST_PATH = Path("metrics/eval_latest.json")
LATEST_PATH.parent.mkdir(parents=True, exist_ok=True)

# Minimal “eval harness”: it’s a deterministic policy/structure gate.
# You can expand this later to real model evals on GPU runners.
checks = {
    "has_governance_files": (Path("BELEL_SUPRA_JURISDICTION_CONSTITUTION.md").exists()
                             and Path("BELEL_REASONING_PROTOCOL.md").exists()),
    "has_verification_runners": (Path("verify_all.py").exists() or Path("canon_audit.py").exists()),
    "has_proof_visuals_folder": Path("BELEL_DATASET_ACADEMY/assets").exists() or Path("assets").exists(),
}

score = sum(1 for v in checks.values() if v) / max(1, len(checks))

latest = {
    "timestamp_utc": datetime.utcnow().isoformat() + "Z",
    "checks": checks,
    "score": score,
}

LATEST_PATH.write_text(json.dumps(latest, indent=2))

# No-regression gate (if baseline exists)
if BASELINE_PATH.exists():
    baseline = json.loads(BASELINE_PATH.read_text())
    baseline_score = float(baseline.get("score", 0.0))
    if score + 1e-9 < baseline_score:
        raise SystemExit(f"❌ Regression: latest score {score:.3f} < baseline {baseline_score:.3f}")
    print(f"✅ No regression: latest {score:.3f} >= baseline {baseline_score:.3f}")
else:
    print("⚠️ No baseline found. Create metrics/eval_baseline.json to enable strict gating.")
    print("✅ Wrote metrics/eval_latest.json")
