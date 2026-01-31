# BELEL_SELF_TEACHING/guide_updater.py
from pathlib import Path
from .curriculum import LEVELS

def ensure_level_files(guide_levels_dir: Path):
    guide_levels_dir.mkdir(parents=True, exist_ok=True)
    for lvl in LEVELS:
        p = guide_levels_dir / f"{lvl}.md"
        if not p.exists():
            p.write_text(f"# {lvl}\n\n", encoding="utf-8")

def append_examples(guide_levels_dir: Path, items: list, cycle_id: str, per_level_cap: int = 12):
    by_level = {lvl: [] for lvl in LEVELS}
    for it in items:
        by_level.get(it["level"], []).append(it)

    for lvl, lst in by_level.items():
        if not lst:
            continue
        p = guide_levels_dir / f"{lvl}.md"
        with p.open("a", encoding="utf-8") as f:
            f.write(f"\n\n## Cycle {cycle_id}\n\n")
            for it in lst[:per_level_cap]:
                f.write(f"### Prompt\n{it['prompt']}\n\n")
                f.write("### Completion\n```text\n")
                f.write(it["completion"][:1600])
                f.write("\n```\n")
                f.write(f"- domain: {it['domain']}\n- verified: {it['verified']}\n- rubric_total: {it['rubric'].get('total')}\n\n")
