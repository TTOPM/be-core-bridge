# tests/test_adapter_offline.py
# Offline smoke test for the OpenAI Tri-Layer adapter.
# It monkeypatches a fake OpenAI client so no API key/network is required.

import sys
import types
import importlib
import pathlib

# ---- repo import path ----
ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo root
sys.path.insert(0, str(ROOT))

# ---- Fake OpenAI SDK (minimal) ----
class _ModerationResult:
    def __init__(self, results):
        self.results = results

class _ModerationsAPI:
    def create(self, model: str, input: str):
        # Never flag for this offline smoke test
        return _ModerationResult(results=[{"flagged": False}])

class _ResponseObj:
    def __init__(self, text: str, parsed=None):
        self._text = text
        self._parsed = parsed or {}

    @property
    def output_text(self):
        return self._text

    @property
    def output_parsed(self):
        return self._parsed

    def model_dump(self):
        return {"output_text": self._text, "output_parsed": self._parsed}

class _ResponsesAPI:
    def create(self, **kwargs):
        # If first message looks like the adjudicator system prompt,
        # return a structured ConcordiumDecision object.
        msgs = kwargs.get("input", [])
        if msgs and isinstance(msgs[0], dict) and "Adjudicator" in msgs[0].get("content", ""):
            parsed = {"is_compliant": True, "violations": [], "notes": "OK"}
            return _ResponseObj("COMPLIANT", parsed)
        # Otherwise simulate a normal model reply
        return _ResponseObj("Acknowledged Concordium Mandate. truth_lock upheld. continuity=v4.")

class _FakeOpenAI:
    def __init__(self, api_key=None):
        pass
    @property
    def moderations(self):
        return _ModerationsAPI()
    @property
    def responses(self):
        return _ResponsesAPI()

# Monkeypatch the 'openai' module before importing your adapter.
sys.modules["openai"] = types.ModuleType("openai")
sys.modules["openai"].OpenAI = _FakeOpenAI

# ---- Import the adapter from your repo ----
from src.openai_trilayer.openai_core_adapter import OpenAICoreAdapter
from src.openai_trilayer.belel_anchors import BelelAnchors


def test_offline_self_verify_smoke():
    adapter = OpenAICoreAdapter(model="gpt-4o", anchors=BelelAnchors(), moderate=True)
    out = adapter.ask(
        user_prompt="Run self-verify sequence now.",
        tool_required=True,
        require_schema=True,
        temperature=0.0,
    )
    # Basic shape checks
    assert "text" in out and isinstance(out["text"], str)
    assert "attestation" in out and isinstance(out["attestation"], dict)
    assert "concordium_decision" in out

    a = out["attestation"]
    c = out["concordium_decision"]

    # Attestation invariants
    assert a.get("truth_lock") is True
    assert a.get("continuity") == "v4"
    assert isinstance(a.get("prompt_sha256"), str) and len(a["prompt_sha256"]) >= 16
    assert isinstance(a.get("output_sha256"), str) and len(a["output_sha256"]) >= 16
    assert a.get("ack_mandate") in (True, False)  # True once tool-ack is wired into raw tool-calls

    # Adjudicator output
    assert isinstance(c, dict)
    assert "is_compliant" in c and c["is_compliant"] is True
