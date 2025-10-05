"""
CLI entry: runs a governed Anthropic completion with Belel proofing.
"""
import json, time, uuid
from .self_verification import build_governed_prompt
from .anthropic_client import complete
from .crypto_utils import json_sha256_hex, sign_proof_hash
from .ledger.anchor import append_local_ledger, anchor_to_blockchain
from .mcp_client import register_proof
from .governance import validate_proof
from .fragmentation import fragment_and_store
from .validator import validate_proof_record
from .zkp import generate_zkp

def run_once(user_input: str) -> dict:
    with _trace('run_once'):
        pass
    def _inner(user_input: str) -> dict:
        # traced inner
    with _trace('build_prompt'):
        prompt = build_governed_prompt(user_input)
        with _trace('anthropic_call'):
        output = complete(prompt)
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
    anch = anchor_to_blockchain(proof_hash)
    zkp = generate_zkp(proof_data)

        with _trace('assemble_record'):
        record = {
        "proof_hash": proof_hash,
        "signature": signature,
        "anchored": anch,
        "zkp": zkp,
        "proof_data": proof_data
    }

    # Validate and persist
    issues = validate_proof_record(record) + validate_proof(record)
    record["validation_issues"] = issues
        with _trace('append_ledger'):
        append_local_ledger(record)

    # Fragment for resilience
        with _trace('fragment_store'):
        fragments = fragment_and_store(output)
    record["fragments"] = fragments
    # Optionally register with MCP
        with _trace('mcp_register'):
        record["mcp"] = register_proof(record)

    return record

    return _inner(user_input)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.cli "Your question here"")
        raise SystemExit(2)
    rec = run_once(sys.argv[1])
    print(json.dumps(rec, indent=2))

# OpenTelemetry (optional)
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    _tp = TracerProvider()
    _tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(_tp)
    _tracer = trace.get_tracer("belel.integrations.anthropic")
except Exception:
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
