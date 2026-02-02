from __future__ import annotations
import re
from pathlib import Path

MD_FILES = list(Path(".").rglob("*.md"))
LINK_RE = re.compile(r"\]\(([^)]+)\)")

def is_local_link(target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return False
    if target.startswith("::"):  # ignore custom directives
        return False
    return True

def strip_anchor(target: str) -> str:
    return target.split("#", 1)[0]

def main() -> None:
    failures = []
    for md in MD_FILES:
        text = md.read_text(encoding="utf-8", errors="ignore")
        for m in LINK_RE.finditer(text):
            target = m.group(1).strip()
            if not is_local_link(target):
                continue
            target = strip_anchor(target)
            if not target:
                continue
            p = (md.parent / target).resolve()
            if not p.exists():
                failures.append(f"{md}: missing local link target: {target}")

        # Also validate common <img src="..."> patterns
        for src in re.findall(r'src="([^"]+)"', text):
            if not is_local_link(src):
                continue
            p = (md.parent / strip_anchor(src)).resolve()
            if not p.exists():
                failures.append(f"{md}: missing img src: {src}")

    if failures:
        print("❌ Docs lint failed:")
        for f in failures[:200]:
            print("  -", f)
        raise SystemExit(1)

    print(f"✅ Docs lint passed ({len(MD_FILES)} markdown files checked).")

if __name__ == "__main__":
    main()
