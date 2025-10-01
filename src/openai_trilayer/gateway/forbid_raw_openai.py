"""
CI/Pre-commit guard: fail if `from openai` or `OpenAI(` appear outside `src/openai_trilayer`.
"""
import sys, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWED = ROOT / "src" / "openai_trilayer"

violations = []
for p in ROOT.rglob("*.py"):
    if ALLOWED in p.parents: 
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"\bfrom\s+openai\b|\bOpenAI\s*\(", txt):
        violations.append(str(p))

if violations:
    print("Forbidden direct OpenAI usage in:", *violations, sep="\n- ")
    sys.exit(1)
