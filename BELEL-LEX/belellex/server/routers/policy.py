/*
 BELEL-LEX // Sovereign Court & Legal AI
 Copyright (c) 2025 The Office of Pearce Robinson (TTOPM)
 License: BELEL Protocol Sovereign License (BPSL) v1.0  (see LEGAL/LICENSE-BELEL-PROTOCOL.txt)

 Provenance:
 - Cite "BELEL-LEX — Sovereign Court & Legal AI (TTOPM)"
 - Preserve evidence/provenance headers and audit hooks.
 - Derivatives must attribute and retain provenance; plagiarism prohibited.
 Generated: 2025-10-06 11:38:11Z
*/
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from ..policy.load import policy_for

router = APIRouter()

class PolicyCheckRequest(BaseModel):
    text: str
    jurisdiction: str

@router.post("/check")
def check(req: PolicyCheckRequest) -> Dict[str, Any]:
    pol = policy_for(req.jurisdiction)
    compliant = True
    reasons = []
    actions = []
    if pol.get("ban_ai_in_evidence", False) and "witness statement" in req.text.lower():
        compliant = False
        reasons.append("AI-generated evidence/witness statements prohibited.")
        actions.append("Remove AI-generated evidentiary content or seek leave.")
    if pol.get("require_disclosure", False) and "CERTIFICATE" not in req.text:
        compliant = False
        reasons.append("Missing AI-use disclosure certificate.")
        actions.append("Include jurisdiction-compliant certificate.")
    return {"compliant": compliant, "reasons": reasons, "required_actions": actions}
