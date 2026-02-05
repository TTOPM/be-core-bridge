from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

from ..settings import settings
from ..schemas.lang import LangReportResponse, LanguageItem, LangGates
from ..core.paths import resolve_sandbox_root

router = APIRouter(tags=["lang"])


@router.get("/api/lang/report", response_model=LangReportResponse)
def lang_report():
    """
    Loads language_count_report.json from your sandbox.

    Convention:
      outputs/reports/language_count_report.json

    Expected shape:
      {
        "documented_count": 132,
        "languages": [{"code":"en","name":"English","tier":"stable"}, ...]
      }
    """
    root = resolve_sandbox_root(settings.out_dir)
    p = root / "reports" / "language_count_report.json"

    if not p.exists():
        # still return a valid, explicit report
        return LangReportResponse(
            documented_count=0,
            languages=[],
            gates=LangGates(block_unsupported=True, warn_experimental=True),
        )

    data = json.loads(p.read_text(encoding="utf-8"))
    langs = []
    for item in data.get("languages") or []:
        langs.append(
            LanguageItem(
                code=str(item.get("code")),
                name=str(item.get("name")),
                tier=str(item.get("tier") or "stable"),
            )
        )

    documented_count = int(data.get("documented_count") or len(langs))
    return LangReportResponse(
        documented_count=documented_count,
        languages=langs,
        gates=LangGates(block_unsupported=True, warn_experimental=True),
    )
    )
