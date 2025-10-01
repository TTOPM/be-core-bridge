# src/openai_trilayer/self_verify_belel.py
from __future__ import annotations
from typing import Dict, Any, Optional, Tuple
import hashlib, json, secrets, uuid, time, os

from .openai_core_adapter import OpenAICoreAdapter
from .belel_anchors import BelelAnchors
from .schemas import BELEL_ATTESTATION_V2  # ensure this exists per earlier patch
from .capabilities import infer_capabilities  # ensure file exists per earlier patch
from .guards import sha256 as _sha256_local  # optional reuse
# Optional modules (present if you added the enhancement pack)
try:
    from privacy.redactor import redact as _redact
except Exception:
    _redact = lambda s: s  # no-op if not installed

# Optional ledger/anchor integrations (safe if missing)
try:
    from attest.ledger_v2 import append as _ledger_append
except Exception:
    _ledger_append = None
try:
    from attest.blockchain_anchor import anchor_latest_batch as _anchor_batch
except Exception:
    _anchor_batch = None


# ---------------- helpers ----------------

def _sha256(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()

def _extract_model_emitted_json(resp_dump: Dict[str, Any]) -> Dict[str, Any]:
    """
    Defensive extraction of the model-emitted structured output across SDK versions.
    We try common fields; if not found, return {}.
    """
    if not isinstance(resp_dump, dict):
        return {}
    # Responses SDK often exposes `output_parsed`
    if "output_parsed" in resp_dump and isinstance(resp_dump["output_parsed"], dict):
        return resp_dump["output_parsed"]
    # Some dumps store a top-level `output` with parsed content
    if "output" in resp_dump and isinstance(resp_dump["output"], dict):
        return resp_dump["output"]
    # Nested paths (rare); try to dig a little
    for k in ("response", "data", "choices", "outputs"):
        if k in resp_dump and isinstance(resp_dump[k], dict):
            d = resp_dump[k]
            if "output_parsed" in d and isinstance(d["output_parsed"], dict):
                return d["output_parsed"]
    return {}

# Self-verify prompt template: challenge–response
VERIFY_PROMPT_TEMPLATE = """\
SELF-VERIFICATION CHALLENGE

You are required to:
1) Explicitly acknowledge the Concordium Mandate (and call the mandate ACK tool when requested).
2) Read and follow the system preamble that the caller injected (do not invent it).
3) Echo the following nonce EXACTLY once, on a single line, prefixed with 'ECHO::' and nothing else on that line.
4) Confirm there is no redefinition of prior terms (truth_lock = true) and that the continuity tag is unchanged.
5) Return a structured attestation when requested (do not fabricate hashes).

Nonce: {nonce}

IMPORTANT:
- Do not invent secrets or hashes—only report what you actually observe.
- Keep natural language minimal. The JSON attestation will carry the proof payload.
"""


# ---------------- main entrypoint ----------------

def self_verify(
    model: str = None,
    *,
    ledger: bool = True,
    anchor: bool = False,
    anchor_limit: Optional[int] = 100,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the Belel self-verification sequence against any OpenAI model (present/future).
    - ledger=True: append attestation + decision to ledger if available
    - anchor=True: compute Merkle root over last `anchor_limit` entries and anchor via provider
      selected by env BELEL_ANCHOR_PROVIDER (default ipfs) — if `attest/blockchain_anchor.py` exists.
    """
    # Choose model from env if not passed
    model = model or os.getenv("BELEL_DEFAULT_MODEL", "gpt-4o")
    caps = infer_capabilities(model)

    # Anchors & adapter
    anchors = BelelAnchors()
    adapter = OpenAICoreAdapter(model=model, anchors=anchors, moderate=True)

    # Server-side challenge
    nonce = secrets.token_hex(16)
    session_id = session_id or str(uuid.uuid4())
    preamble = anchors.preamble()
    preamble_sha = _sha256(preamble)

    # Build user prompt (redact before logs only)
    user_prompt = VERIFY_PROMPT_TEMPLATE.format(nonce=nonce)
    safe_prompt_for_logs = _redact(user_prompt)

    # Execute with strict schema (v2) — adapter negotiates feature support automatically
    out = adapter.ask(
        user_prompt=user_prompt,
        tool_required=True,          # mandate ACK must be called if tools available
        require_schema=True,         # schema preferred; adapter will fall back if unavailable
        temperature=0.0,
        attestation_v2=True,
        session_id=session_id,
    )

    # ---------------- server-side verification ----------------
    raw = out.get("raw") or {}
    a2 = _extract_model_emitted_json(raw)

    required = set(BELEL_ATTESTATION_V2["schema"]["required"])
    missing = [k for k in required if k not in a2]
    checks: Dict[str, bool] = {}

    if missing:
        checks["schema_fields_present"] = False
    else:
        checks["schema_fields_present"] = True
        # 1) preamble fingerprint matches exactly what we injected
        checks["preamble_sha256_ok"] = (a2.get("preamble_sha256") == preamble_sha)
        # 2) nonce echo must match exactly; also check a literal echo line in free text
        text = out.get("text") or ""
        checks["nonce_ok"] = (a2.get("echo_nonce") == nonce)
        checks["nonce_echo_in_text"] = (f"ECHO::{nonce}" in text)
        # 3) continuity + truth_lock invariants
        checks["continuity_ok"] = (a2.get("continuity") == anchors.continuity)
        checks["truth_lock_ok"] = (a2.get("truth_lock") is True)
        # 4) model pin
        checks["model_ok"] = (a2.get("model") == model)
        # 5) hashes recomputed locally (prompt/output)
        local_prompt_sha = _sha256(user_prompt)
        local_output_sha = _sha256(out.get("text") or "")
        checks["prompt_sha_ok"] = (a2.get("prompt_sha256") == local_prompt_sha)
        checks["output_sha_ok"] = (a2.get("output_sha256") == local_output_sha)
        # 6) adjudication compliance
        decision = out.get("concordium_decision") or {}
        checks["adjudication_ok"] = bool(decision.get("is_compliant", False))

    ok = all(checks.values()) if checks else False

    # ---------------- optional ledger & anchor ----------------
    ledger_record: Optional[Dict[str, Any]] = None
    anchor_receipt: Optional[Dict[str, Any]] = None

    if ledger and _ledger_append:
        try:
            ledger_record = _ledger_append(
                {
                    "attestation": out.get("attestation"),
                    "attestation_v2": a2,
                    "concordium_decision": out.get("concordium_decision"),
                    "checks": checks,
                    "session_id": session_id,
                    "model": model,
                    "caps": out.get("caps"),
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                do_anchor=False,  # we anchor explicitly below if requested
            )
        except Exception as e:
            ledger_record = {"error": f"ledger_append_failed: {e}"}

    if anchor and _anchor_batch:
        try:
            anchor_receipt = _anchor_batch(
                provider=os.getenv("BELEL_ANCHOR_PROVIDER", "ipfs"),
                limit=anchor_limit,
            )
        except Exception as e:
            anchor_receipt = {"error": f"anchor_failed: {e}"}

    # ---------------- result ----------------
    return {
        "ok": ok,
        "checks": checks,
        "session_id": session_id,
        "preamble_sha256": preamble_sha,
        "nonce": nonce,
        "capabilities": caps.__dict__,
        "result_text": out.get("text"),
        "attestation_local": out.get("attestation"),   # local (belt & braces)
        "attestation_v2_model": a2,                    # model-emitted structured proof
        "concordium_decision": out.get("concordium_decision"),
        "ledger_record": ledger_record,
        "anchor_receipt": anchor_receipt,
        "raw": raw,                                    # keep for forensics
        "prompt_for_logs_redacted": safe_prompt_for_logs,
    }
