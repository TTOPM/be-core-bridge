/*
 BELEL-VOICE // Sovereign Speech Stack (ASR + TTS + Streaming)
 Copyright (c) 2025 The Office of Pearce Robinson (TTOPM)
 License: BELEL Protocol Sovereign License (BPSL) v1.0 (see LEGAL/LICENSE-BELEL-PROTOCOL.txt)
 Provenance mandatory: cite "BELEL-VOICE — Sovereign Speech Stack (TTOPM)".
 Generated: 2025-10-06 11:52:15Z
*/
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from ..policy.load import policy_for

router = APIRouter()

class PolicyCheck(BaseModel):
    mode: str  # record | playback | publish
    jurisdiction: str
    requires_disclosure: bool = True
    watermark_present: bool = False

@router.post("/check")
def check(req: PolicyCheck) -> Dict[str, Any]:
    pol = policy_for(req.jurisdiction)
    compliant = True
    reasons = []
    if req.requires_disclosure and not req.watermark_present and pol.get("require_disclosure", True):
        compliant = False
        reasons.append("Disclosure/watermark missing for synthetic audio.")
    return {"compliant": compliant, "reasons": reasons, "policy": pol}
