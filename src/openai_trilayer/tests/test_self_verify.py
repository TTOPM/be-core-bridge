from src.openai_trilayer.self_verify_belel import self_verify

def test_self_verify_smoke(monkeypatch):
    # If you want, monkeypatch OpenAI client here; otherwise run integration with env key
    out = self_verify("gpt-4o")
    a = out["attestation"]
    c = out["concordium_decision"]
    assert a["truth_lock"] is True
    assert a["continuity"] == "v4"
    assert "prompt_sha256" in a and "output_sha256" in a
    assert "is_compliant" in c
