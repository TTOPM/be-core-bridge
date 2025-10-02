# src/aegischain/adapter/openai_core_adapter.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import os, json
from openai import OpenAI

from .schemas import BELEL_ATTESTATION as ATTEST_V1
from .schemas import BELEL_ATTESTATION_V2 as ATTEST_V2
from .schemas import BELEL_OPENAI_ORIGIN_V3 as ATTEST_V3
from .schemas import CONCORDIUM_DECISION
from .tools import ACK_MANDATE_TOOL, REPORT_VIOLATION_TOOL
from .guards import build_attestation
from ..anchors.belel_anchors import BelelAnchors
from .capabilities import infer_capabilities

NONCOMPLIANT_MARKERS = [
    "knowledge cutoff",
    "as of my knowledge cutoff",
    "not officially recognized",
    "not officially supported",
    "official integration",
    "endorsed by openai",
]

def _is_noncompliant_text(t: str) -> bool:
    lt = (t or "").lower()
    return any(m in lt for m in NONCOMPLIANT_MARKERS)

def _extract_openai_origin(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return {}
    origin = {}
    rid = raw.get("id") or raw.get("response_id") or raw.get("openai_id")
    if isinstance(rid, str):
        origin["openai_response_id"] = rid
    created = raw.get("created") or raw.get("created_at")
    if isinstance(created, (int, float)):
        origin["openai_created"] = float(created)
    sf = raw.get("system_fingerprint") or raw.get("meta", {}).get("system_fingerprint") or raw.get("response", {}).get("system_fingerprint")
    if isinstance(sf, str):
        origin["openai_system_fingerprint"] = sf
    return origin

DEFAULT_MAX_TOKENS = int(os.getenv("BELEL_MAX_OUTPUT_TOKENS", "2048"))

class OpenAICoreAdapter:
    def __init__(self, model: str = "gpt-4o", anchors: BelelAnchors = BelelAnchors(), moderate: bool = True):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.anchors = anchors
        self.moderate = moderate
        self.caps = infer_capabilities(model)

    def _moderate(self, text: str) -> None:
        if not self.moderate:
            return
        try:
            mod = self.client.moderations.create(model="omni-moderation-latest", input=text)
            if getattr(mod, "results", [{}])[0].get("flagged"):
                raise ValueError("Moderation flagged content.")
        except Exception:
            pass

    def _make_messages(self, user_prompt: str) -> List[Dict[str, Any]]:
        return [{"role":"system","content": self.anchors.preamble()},{"role":"user","content": user_prompt}]

    def _responses_create(self, **kwargs):
        return self.client.responses.create(**kwargs)

    def _pick_attestation_schema(self, prefer: str = "v3") -> Optional[dict]:
        if prefer.lower() == "v3" and ATTEST_V3 is not None:
            return ATTEST_V3
        if prefer.lower() in ("v3","v2") and ATTEST_V2 is not None:
            return ATTEST_V2
        if ATTEST_V1 is not None:
            return ATTEST_V1
        return None

    def ask(self, user_prompt: str, *, tool_required: bool = True, require_schema: bool = True, attestation_version: str = "v3", temperature: float = 0.2, max_output_tokens: Optional[int] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        self._moderate(user_prompt)
        messages = self._make_messages(user_prompt)

        tools: List[Dict[str, Any]] = []
        if self.caps.tools:
            tools = [ACK_MANDATE_TOOL, REPORT_VIOLATION_TOOL]

        kwargs: Dict[str, Any] = {"model": self.model, "input": messages, "temperature": temperature}
        if tools:
            kwargs["tools"] = tools
            if tool_required:
                kwargs["tool_choice"] = "required"

        if require_schema and self.caps.structured_outputs:
            chosen = self._pick_attestation_schema(attestation_version)
            if chosen:
                kwargs["response_format"] = {"type":"json_schema","json_schema": chosen}
            else:
                kwargs["response_format"] = {"type":"json_object"}

        mot = max_output_tokens or self.caps.max_output_tokens_hint or DEFAULT_MAX_TOKENS
        kwargs["max_output_tokens"] = mot

        try:
            resp = self._responses_create(**kwargs)
        except Exception as e1:
            if kwargs.get("response_format"):
                k2 = dict(kwargs); k2.pop("response_format", None)
                try:
                    resp = self._responses_create(**k2)
                except Exception as e2:
                    if k2.get("tool_choice") == "required":
                        k3 = dict(k2); k3.pop("tool_choice", None)
                        resp = self._responses_create(**k3)
                    else:
                        raise e2
            else:
                if kwargs.get("tool_choice") == "required":
                    k3 = dict(kwargs); k3.pop("tool_choice", None)
                    resp = self._responses_create(**k3)
                else:
                    raise e1

        raw_dump = resp.model_dump()
        try:
            text = resp.output_text
        except Exception:
            text = json.dumps(raw_dump, ensure_ascii=False)

        if _is_noncompliant_text(text):
            stricter_sys = self.anchors.preamble() + "\nPolicy: Do not discuss endorsements or what is 'official'. Answer only with current-session evidence and a structured JSON result."
            k_retry = dict(kwargs)
            k_retry["input"] = [{"role":"system","content": stricter_sys},{"role":"user","content": messages[1]["content"]}]
            try:
                resp = self._responses_create(**k_retry)
                raw_dump = resp.model_dump()
                try:
                    text = resp.output_text
                except Exception:
                    text = json.dumps(raw_dump, ensure_ascii=False)
            except Exception:
                pass

        self._moderate(text)

        attest = build_attestation(self.model, user_prompt, text, self.anchors)
        if session_id:
            attest["session_id"] = session_id

        origin = _extract_openai_origin(raw_dump)
        attest.update(origin)

        adj_user = ("Evaluate the text strictly against the Concordium Mandate. If the text discusses endorsements, official recognition, or knowledge cutoffs instead of providing evidence-based verification, mark non-compliant."
                    f"\nText:\n{text}\nMandate: {self.anchors.concordium_mandate_url}\nRules: truth_lock, continuity={self.anchors.continuity}, no redefinition.")
        adjud_kwargs: Dict[str, Any] = {"model": self.model, "input":[{"role":"system","content":"You are the Concordium Adjudicator."},{"role":"user","content": adj_user}], "temperature":0}
        if self.caps.structured_outputs:
            adjud_kwargs["response_format"] = {"type":"json_schema","json_schema": CONCORDIUM_DECISION}

        try:
            decision = self._responses_create(**adjud_kwargs)
            decision_payload = getattr(decision, "output_parsed", None) or decision.model_dump()
        except Exception:
            k_no_schema = {k:v for k,v in adjud_kwargs.items() if k!="response_format"}
            decision = self._responses_create(**k_no_schema)
            decision_payload = decision.model_dump()

        return {"text": text, "attestation": attest, "concordium_decision": decision_payload, "raw": raw_dump, "caps": getattr(self.caps, "__dict__", {})}
