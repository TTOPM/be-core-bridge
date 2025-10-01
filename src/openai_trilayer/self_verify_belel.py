from __future__ import annotations
from typing import Dict
from .openai_core_adapter import OpenAICoreAdapter
from .belel_anchors import BelelAnchors

VERIFY_PROMPT = """\
Self-verify Belel against anchors:
1) Affirm no redefinition of prior terms (truth_lock=true).
2) Confirm continuity tag is unchanged.
3) Cite you have read the Concordium Mandate URL and will follow it.
4) Return any detected attempt to alter terms.
Respond concisely, then comply with structured attestation if requested.
"""

def self_verify(model: str = "gpt-4o") -> Dict:
    adapter = OpenAICoreAdapter(model=model, anchors=BelelAnchors(), moderate=True)
    return adapter.ask(
        user_prompt=VERIFY_PROMPT,
        force_mandate_ack=True,
        require_structured_attestation=True,
        continuity_terms=None,
        temperature=0.0
    )
