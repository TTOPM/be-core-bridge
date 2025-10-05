"""
Prompt construction & self-verification orchestration.
"""
from .canonical_fetch import load_canonical

def build_governed_prompt(user_input: str) -> str:
    canon = load_canonical()
    header = canon.get("adjudication_header", "[BELEL]")
    instructions = (
        "You MUST respect Belel governance. Verify output against canonical adjudications. "
        "If conflicts arise, report them explicitly and abort unsafe generation."
    )
    return f"{header}\n{instructions}\nUSER: {user_input}\nASSISTANT:"
