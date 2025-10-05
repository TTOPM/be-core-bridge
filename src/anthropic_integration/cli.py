#!/usr/bin/env python3
"""
Belel × Anthropic CLI
- Builds a Belel-governed prompt
- Calls Anthropic (Claude) via official SDK
- Creates a signed, anchorable proof record
- Optionally registers the proof with an MCP registry
- Optionally fragments output for resilience
"""

from __future__ import annotations
import os
import sys
import json
import time
import uuid
import argparse
from typing import Any, Dict

# --- Local imports (same folder/module) ---
from .self_verification import build_governed_prompt
from .anthropic_client import complete  # uses Anthropic Messages API
from .crypto_utils import json_sha256_hex, sign_proof_hash
from .ledger.anchor import append_local_ledger, anchor_to_blockchain
from .mcp_client import register_proof
from .validator import validate_proof_record
from .governance import validate_proof
from .fragmentation import fragment_and_store
from .zkp import generate_zkp

# Optional tracing (safe if not installed/configured)
try:
    from opentelemetry import trace  # type: ignore
    _tracer = trace.get_tracer("belel.anthropic.cli")
except Exception:  # pragma: no cover
    _tracer = None


def _trace(name: str):
    class _Ctx:
        def __enter__(self):
            if _tracer:
                self.span = _tracer.start_span(name)
                return self.span
            return None
        def __exit__(self, exc_type, exc, tb):
            if _tracer:
                self.span.end()
    return _Ctx()


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None else default


def run_once(
    user_input: str,
    model: str | None = None,
    max_tokens: int = 800,
    temperature: float = 0.2,
    do_mcp: bool = True,
    do_fragments: bool = True
) -> Dict[str, Any]:
    """Execute one governed Anthropic interaction and return the proof record."""
    with _trace("build_prompt"):
        prompt = build_governed_prompt(user_input)

    with _trace("anthropic_call"):
        output = complete(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )

    with _trace("assemble_proof"):
        proof_data = {
            "id": str(uuid.uuid4()),
            "timestamp": int(time.time()),
            "protocol": "Belel-Concordium-Mandate",
            "input": user_input,
            "prompt": prompt,
            "output": output
        }
        proof_hash = json_sha256_hex(proof_data)
        signature = sign_proof_hash(proof_hash)
        anchored = anchor_to_blockchain(proof_hash)
        zkp = generate_zkp(proof_data)

        record = {
            "proof_hash": proof_hash,
            "signature": signature,
            "anchored": anchored,
            "zkp": zkp,
            "proof_data": proof_data
        }

    with _trace("validate"):
        issues = validate_proof_record(record) + validate_proof(record)
        record["validation_issues"] = issues

    with _trace("ledger_append"):
        append_local_ledger(record)

    if do_fragments:
        with _trace("fragment_store"):
            frags = fragment_and_store(output)
            record["fragments"] = frags
    else:
        record["fragments"] = []

    if do_mcp:
        with _trace("mcp_register"):
            record["mcp"] = register_proof(record)
    else:
        record["mcp"] = {"status": "skipped"}

    return record


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        description="Belel × Anthropic – governed CLI (proof-bonded)"
    )
    p.add_argument("query", help="User query to send through governed Anthropic flow.")
    p.add_argument("--model", help="Anthropic model (env ANTHROPIC_MODEL used if unset).")
    p.add_argument("--max-tokens", type=int, default=800, help="Max tokens for Claude.")
    p.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    p.add_argument("--no-mcp", action="store_true", help="Skip MCP registry registration.")
    p.add_argument("--no-fragments", action="store_true", help="Skip output fragmentation.")
    p.add_argument("--json", action="store_true", help="Print the full proof record JSON.")
    args = p.parse_args(argv)

    # Allow model override via env if not set on CLI.
    model = args.model or _env("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")

    rec = run_once(
        user_input=args.query,
        model=model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        do_mcp=not args.no_mcp,
        do_fragments=not args.no_fragments
    )

    if args.json:
        print(json.dumps(rec, indent=2))
    else:
        # Human-readable summary
        sig_scheme = rec["signature"].get("scheme")
        mcp_stat = rec.get("mcp", {}).get("status")
        anchor = rec["anchored"]
        print("\n=== Belel × Anthropic (Governed) ===")
        print(f"Proof Hash : {rec['proof_hash']}")
        print(f"Signature  : {sig_scheme}")
        print(f"Anchoring  : {anchor.get('provider')} -> {anchor.get('status')} (txid={anchor.get('txid')})")
        print(f"MCP        : {mcp_stat}")
        if rec.get("validation_issues"):
            print("Validation : issues ->", rec["validation_issues"])
        else:
            print("Validation : OK")
        print("\n--- Output (first 800 chars) ---")
        out = rec["proof_data"]["output"] or ""
        print(out[:800])
        print("\n--- Fragments ---")
        for fp in rec.get("fragments", []):
            print("•", fp)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
