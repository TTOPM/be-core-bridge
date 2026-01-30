def test_live_gate():
    from ..governance.live_gate import LiveVisionGate
    gate = LiveVisionGate(LIVE_POLICY)
    assert gate.allow_input("describe room", "safe scene")
    assert not gate.allow_input("scan faces", "person without consent")
