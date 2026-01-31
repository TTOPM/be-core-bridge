# BELEL_SELF_TEACHING/guide_compiler.py
from pathlib import Path
from .curriculum import LEVELS
import json

def compile_master(guide_levels_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    master_md = out_dir / "MASTER_GUIDE.md"
    master_json = out_dir / "MASTER_GUIDE.json"

    md_parts = []
    json_parts = []

    for lvl in LEVELS:
        p = guide_levels_dir / f"{lvl}.md"
        if p.exists():
            content = p.read_text(encoding="utf-8")
            md_parts.append(content)
            json_parts.append({"level": lvl, "content": content})

    master_md.write_text("\n\n---\n\n".join(md_parts), encoding="utf-8")
    master_json.write_text(json.dumps(json_parts, ensure_ascii=False, indent=2), encoding="utf-8")
