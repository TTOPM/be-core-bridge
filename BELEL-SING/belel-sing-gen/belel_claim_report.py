# BELEL-SING/belel-sing-gen/belel_claim_report.py
from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path
from typing import Dict, Any

import torch

from belel_benchmark_ultra import main as run_benchmark_main


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="benchmarks/claim_report.json")
    ap.add_argument("--note", default="BELEL claim report (generated locally)")
    args, _ = ap.parse_known_args()

    # This script assumes you run belel_benchmark_ultra.py normally.
    # Claim report: environment + pointer to latest benchmark summary.
    # (Next iteration: auto-run benchmark here if you want.)
    env = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda": torch.version.cuda if hasattr(torch.version, "cuda") else "",
        "cudnn": torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else "",
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        "note": str(args.note),
    }

    # Find latest benchmark summary if it exists
    bench_root = Path("benchmarks/belel_ultra")
    latest = None
    if bench_root.exists():
        dirs = sorted([p for p in bench_root.iterdir() if p.is_dir()], reverse=True)
        for d in dirs:
            summ = d / "benchmark_summary.json"
            if summ.exists():
                latest = str(summ)
                break

    report = {
        "env": env,
        "latest_benchmark_summary": latest or "",
        "claim_template": {
            "format": "Generate DURATION seconds in X seconds on GPU with pass_rate >= Y under BelelBenchmarkProtocol gates.",
            "how_to_publish": "Attach claim_report.json + benchmark_summary.json + checkpoint hashes.",
        },
    }

    _write_json(Path(args.out), report)
    print("wrote:", args.out)


if __name__ == "__main__":
    main()
