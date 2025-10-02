# src/aegischain/adjudicator/quorum.py
from typing import List, Dict, Any

def quorum_decide(decisions: List[Dict[str, Any]], threshold: float = 0.66) -> Dict[str, Any]:
    total = len(decisions)
    if total == 0:
        return {"is_compliant": False, "violations": ["no_decisions"]}
    compliant = sum(1 for d in decisions if d.get("is_compliant"))
    ok = (compliant / total) >= threshold
    return {"is_compliant": ok, "violations": [] if ok else ["quorum_failed"], "tally": {"compliant": compliant, "total": total}}
