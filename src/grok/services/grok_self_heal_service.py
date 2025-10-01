from __future__ import annotations
import os, time, logging
from grok_integrity_beacon import BeaconEmitter
from grok_self_heal import SelfHealContext, SelfHealStateMachine

# Adapters to your real modules
from grok.adapters.anchors_adapter import AnchorsAdapter
from grok.adapters.concordium_adapter import ConcordiumAdapter
from grok.adapters.audit_adapter import AuditAdapter
from grok.adapters.core_adapter import CoreAdapter

logging.basicConfig(level=os.getenv("GROK_LOG_LEVEL", "INFO"))
INTERVAL = int(os.getenv("GROK_SELF_HEAL_INTERVAL_SEC", "60"))

def main() -> None:
    anchors = AnchorsAdapter()          # implements .get('cid','digest','ok') and methods used by SM
    concordium = ConcordiumAdapter()    # reachable(), tip(), try_alt_gateways(), rebind(cid)
    audit = AuditAdapter()              # chain_is_monotone(), last_hash(), replay_from_checkpoint(), rebuild(cid, tail)
    core = CoreAdapter()                # models_ok(), pin_safe_profile(), router_reset()

    ctx = SelfHealContext(anchors=anchors, concordium=concordium, audit=audit, core=core)
    emitter = BeaconEmitter()
    sm = SelfHealStateMachine(ctx, emitter)

    while True:
        sm.run_once()
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
