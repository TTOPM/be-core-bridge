import json
from BELEL_SELF_TEACHING.schemas import SampleSFT

def test_schema_instantiation():
    s = SampleSFT(
        prompt="p",
        completion="c" * 60,
        level="1_Foundations",
        domain="general",
        source="self",
        verified=True,
        verifier={"passed": True},
        rubric={"total": 1.0},
        hash="x",
        cycle_id="2026-01-31T00:00:00Z"
    )
    payload = json.loads(json.dumps(s.__dict__))
    assert "prompt" in payload
    assert "completion" in payload
