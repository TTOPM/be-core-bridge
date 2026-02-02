from __future__ import annotations
import os
import json
from pathlib import Path
from datetime import datetime

# This script validates the *presence* of proof surfaces and expected emitted artifacts.
# It does not run private APIs, does not exfiltrate secrets, and does not publish outputs.

EXPECTED_EXISTENCE = [
    "BELEL_SUPRA_JURISDICTION_CONSTITUTION.md",
    "BELEL_REASONING_PROTOCOL.md",
]

# Optional modules: only check if repo claims them
OPTIONAL_PATHS = [
    "BELEL_DATASET_ACADEMY",
    "BELEL_SELF_TEACHING",
    "chatwithbelel",
    "BELEL-LIVE-VISION",
    "BELEL-VOICE",
    "BELEL-SING",
    "x_bot",
]

# Where “emitted artifacts” usually exist; presence is checked if parent organs exist.
LIKELY_ARTIFACT_DIRS = [
    "metrics",
    "manifests",
    "cycles",
    "generated_shards",
    "quarantine",
    "artifacts",
    "bench",
]

def main() -> None:
    repo = Path(".").resolve()
    report_dir = repo / "proof_reports"
    report_dir.mkdir(exist_ok=True)

    failures = []
    notes = []

    for p in EXPECTED_EXISTENCE:
        if not (repo / p).exists():
            failures.append(f"Missing required file: {p}")

    present_organs = []
    for p in OPTIONAL_PATHS:
        if (repo / p).exists():
            present_organs.append(p)

    # For any present organ, check for at least one “likely artifact” directory somewhere in repo
    found_artifact_dirs = [d for d in LIKELY_ARTIFACT_DIRS if (repo / d).exists()]

    # Stronger rule: if self-teaching exists, require at least a cycles/ or generated_shards/ folder to exist (even empty)
    if (repo / "BELEL_SELF_TEACHING").exists():
        if not ((repo / "cycles").exists() or (repo / "generated_shards").exists() or (repo / "BELEL_SELF_TEACHING" / "cycles").exists()):
            failures.append("Self-teaching present but no cycles/ or generated_shards/ folder found (expected proof surface).")

    # If dataset academy exists, require manifests/ or metrics/
    if (repo / "BELEL_DATASET_ACADEMY").exists():
        if not ((repo / "manifests").exists() or (repo / "metrics").exists() or (repo / "BELEL_DATASET_ACADEMY" / "manifests").exists()):
            failures.append("Dataset Academy present but no manifests/ or metrics/ folder found (expected proof surface).")

    summary = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "present_organs": present_organs,
        "found_artifact_dirs": found_artifact_dirs,
        "failures": failures,
        "notes": notes,
    }

    (report_dir / "proof_surface_summary.json").write_text(json.dumps(summary, indent=2))

    if failures:
        print("❌ Proof surface verification failed:")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)

    print("✅ Proof surface verification passed.")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
