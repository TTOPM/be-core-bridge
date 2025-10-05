from src.cli import run_once

def test_flow():
    rec = run_once("Demo query")
    assert "proof_hash" in rec
    assert rec["proof_data"]["output"].startswith("SIMULATED_ANTHROPIC_OUTPUT")
