# BELEL_SELF_TEACHING/verifiers.py
# This module is a thin adapter around your existing verify_execution()
from typing import Dict, Any

def verify(completion: str, verify_execution) -> Dict[str, Any]:
    """
    verify_execution is injected from belel_core (sandbox).
    Expect: {"passed": bool, "signals": {...}, "errors": [...], "type": "code|math|consistency"}
    """
    res = verify_execution(completion)
    if not isinstance(res, dict) or "passed" not in res:
        return {"passed": False, "signals": {"bad_verifier_contract": True}, "errors": ["invalid_verifier_result"]}
    return res
