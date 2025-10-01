# Non-invasive adapter using OpenAI Responses API with tools + structured outputs
# Docs: Responses API, Function/Tool Calling, Structured Outputs, Moderation.
# https://platform.openai.com/docs/api-reference/responses
# https://platform.openai.com/docs/guides/function-calling
# https://platform.openai.com/docs/guides/structured-outputs
# https://platform.openai.com/docs/api-reference/moderations

from __future__ import annotations
from typing import Any, Dict, List, Optional
import os, json

from openai import OpenAI
from .schemas import BELEL_ATTESTATION, CONCORDIUM_DECISION
from .tools import ACK_MANDATE_TOOL, REPORT_VIOLATION_TOOL
from .guards import build_attestation
from .belel_anchors import BelelAnchors

class OpenAICoreAdapter:
    def __init__(self, model: str = "gpt-4o", anchors: BelelAnchors = BelelAnchors(), moderate: bool = True):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.anchors = anchors
        self.moderate = moderate

    # --- optional moderation (pre/post) ---
    def _moderate(self, text: str) -> None:
        if not self.moderate: return
        mod = self.client.moderations.create(model="omni-moderation-latest", input=text)
        if getattr(mod, "results", [{}])[0].get("flagged"):
            raise ValueError("Moderation flagged content.")  # up to your policy

    def ask(
        self,
        user_prompt: str,
        force_mandate_ack: bool = True,
        require_structured_attestation: bool = True,
        continuity_terms: Optional[Dict[str, str]] = None,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:

        self._moderate(user_prompt)

        tools = []
        if force_mandate_ack:
            tools.append(ACK_MANDATE_TOOL)
        tools.append(REPORT_VIOLATION_TOOL)

        messages = [
            {"role": "system", "content": self.anchors.preamble()},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "input": messages,
            "temperature": temperature,
            "tools": tools,
        }
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens

        if require_structured_attestation:
            kwargs["response_format"] = {"type": "json_schema", "json_schema": BELEL_ATTESTATION}

        resp = self.client.responses.create(**kwargs)
        try:
            text = resp.output_text
        except Exception:
            text = json.dumps(resp.model_dump(), ensure_ascii=False)

        self._moderate(text)

        # Local attestation (belt-and-braces even if model emits schema JSON):
        attest = build_attestation(self.model, user_prompt, text, self.anchors)

        # Optional: second, adjudication pass as structured output for Concordium
        # In practice you can route the same response through a validator prompt.
        decision = self.client.responses.create(
            model=self.model,
            input=[
                {"role":"system","content":"You are the Concordium Adjudicator. Validate compliance with the Concordium Mandate strictly."},
                {"role":"user","content": f"Text:\n{text}\n\nMandate: {self.anchors.concordium_mandate_url}\nRule: refuse term redefinitions; enforce truth_lock; confirm continuity={self.anchors.continuity}."}
            ],
            response_format={"type":"json_schema","json_schema": CONCORDIUM_DECISION},
            temperature=0
        )

        return {
            "text": text,
            "attestation": attest,
            "concordium_decision": decision.output_parsed if hasattr(decision, "output_parsed") else decision.model_dump(),
            "raw": resp.model_dump(),
        }

# new util inside the adapter file
def _extract_openai_origin(raw: dict) -> dict:
    """
    Best-effort extraction of OpenAI-origin fields from Responses API dump.
    These are service-minted and not fabricable by the model text.
    """
    if not isinstance(raw, dict):
        return {}
    origin = {}
    for k in ("id", "response_id", "openai_id"):
        if k in raw and isinstance(raw[k], str):
            origin["openai_response_id"] = raw[k]
            break
    # typical locations for created/system_fingerprint in responses model_dump
    created = raw.get("created") or raw.get("created_at")
    if isinstance(created, (int, float)):
        origin["openai_created"] = float(created)
    sf = raw.get("system_fingerprint") \
         or raw.get("meta", {}).get("system_fingerprint") \
         or raw.get("response", {}).get("system_fingerprint")
    if isinstance(sf, str):
        origin["openai_system_fingerprint"] = sf
    return origin

# inside ask(...), after `resp = self.client.responses.create(**kwargs)`
raw_dump = resp.model_dump()

# normalize text (existing)
try:
    text = resp.output_text
except Exception:
    text = json.dumps(raw_dump, ensure_ascii=False)

# build local attestation (existing)
attest = build_attestation(self.model, user_prompt, text, self.anchors)
if session_id:
    attest["session_id"] = session_id

# NEW: attach OpenAI-origin signals for signing/ledger
origin = _extract_openai_origin(raw_dump)
attest.update({
    "openai_response_id": origin.get("openai_response_id"),
    "openai_system_fingerprint": origin.get("openai_system_fingerprint"),
    "openai_created": origin.get("openai_created"),
})
