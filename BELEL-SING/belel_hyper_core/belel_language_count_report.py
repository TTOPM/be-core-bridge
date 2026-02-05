# BELEL-SING/belel-sing-gen/belel_language_count_report.py
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

from belel_hyper_core.belel_multilang_registry import (
    list_languages,
    marketing_summary,
    registry_digest,
)

def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _safe_write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="language_count_report.json", help="Output JSON path")
    ap.add_argument("--include_all", action="store_true", help="Include unsupported/experimental entries if present")
    ap.add_argument("--include_items", action="store_true", help="Include full item list in report")
    args = ap.parse_args()

    supported_only = not bool(args.include_all)
    langs = list_languages(supported_only=supported_only)

    report: Dict[str, Any] = {
        "utc": _utc_now(),
        "supported_only": bool(supported_only),
        "language_count": len(langs),
        "registry_sha256": registry_digest(),
        "summary": marketing_summary(supported_only=supported_only),
    }

    if args.include_items:
        report["items"] = [
            {
                "bcp47": x.bcp47,
                "iso639_3": x.iso639_3,
                "english_name": x.english_name,
                "native_name": x.native_name,
                "region": x.region,
                "family": x.family,
                "script": x.script,
                "direction": x.direction,
                "supported": x.supported,
                "priority": x.priority,
                "notes": x.notes,
            }
            for x in langs
        ]

    out_path = Path(args.out)
    _safe_write_json(out_path, report)
    print("wrote:", str(out_path.resolve()))
    print("count:", len(langs))
    print("registry_sha256:", report["registry_sha256"])

if __name__ == "__main__":
    main()