from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from .research_log import append_research_log


@dataclass
class ResearchNote:
    title: str
    source: str
    summary: str
    tags: Optional[list[str]] = None


def ingest_research_note(note: ResearchNote, base_dir: Path) -> Path:
    """
    Writes a note to BELEL-CORE-EVOLUTION/research_ingestion/notes/ and logs it.
    """
    notes_dir = base_dir / "research_ingestion" / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = "".join(c for c in note.title if c.isalnum() or c in ("-", "_", " ")).strip().replace(" ", "_")
    out = notes_dir / f"{ts}__{safe}.md"

    tag_line = ""
    if note.tags:
        tag_line = "Tags: " + ", ".join(note.tags) + "\n\n"

    out.write_text(
        f"# {note.title}\n\n"
        f"Source: {note.source}\n"
        f"{tag_line}"
        f"{note.summary}\n",
        encoding="utf-8",
    )

    append_research_log(
        base_dir=base_dir,
        entry={
            "ts": ts,
            "title": note.title,
            "source": note.source,
            "path": str(out.relative_to(base_dir)),
            "tags": note.tags or [],
        },
    )

    return out
