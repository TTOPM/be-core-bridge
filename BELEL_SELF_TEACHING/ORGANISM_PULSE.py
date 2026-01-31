# ORGANISM_PULSE.py (snippet)
from datetime import datetime, timezone

def should_run_self_teaching(now_utc: datetime, state: dict) -> bool:
    # deterministic schedule > random
    # e.g., run every 6 hours
    last = state.get("last_self_teaching_utc")
    if not last:
        return True
    elapsed = (now_utc - datetime.fromisoformat(last)).total_seconds()
    return elapsed >= 6 * 3600

# inside pulse:
now = datetime.now(timezone.utc)
if should_run_self_teaching(now, organism_state):
    import belel_core
    from BELEL_SELF_TEACHING.BELEL_SELF_TEACHING_GENERATOR import run_self_teaching_cycle
    out = run_self_teaching_cycle(belel_core)
    organism_state["last_self_teaching_utc"] = now.replace(microsecond=0).isoformat()
    organism_state["last_self_teaching_result"] = out["metrics"]
