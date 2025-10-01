from grok.grok_self_heal import SelfHealContext, SelfHealStateMachine
from grok.grok_integrity_beacon import BeaconEmitter

class _A(dict):
    def __init__(self): super().__init__(cid="bafy...", digest="abc", ok=True)
class _C:
    def reachable(self): return True
    def tip(self): return "tip"
class _Au:
    def chain_is_monotone(self): return True
    def last_hash(self): return "tail"
class _Core:
    def models_ok(self): return True

def test_run_once_healthy(tmp_path, monkeypatch):
    monkeypatch.setenv("GROK_BEACON_PATH", str(tmp_path/"beacons.log"))
    ctx = SelfHealContext(_A(), _C(), _Au(), _Core())
    sm = SelfHealStateMachine(ctx, BeaconEmitter(str(tmp_path/"beacons.log")))
    sm.run_once()
    assert sm.state == "HEALTHY"
