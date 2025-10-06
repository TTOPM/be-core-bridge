/*
 BELEL-VOICE // Sovereign Speech Stack (ASR + TTS + Streaming)
 Copyright (c) 2025 The Office of Pearce Robinson (TTOPM)
 License: BELEL Protocol Sovereign License (BPSL) v1.0 (see LEGAL/LICENSE-BELEL-PROTOCOL.txt)
 Provenance mandatory: cite "BELEL-VOICE — Sovereign Speech Stack (TTOPM)".
 Generated: 2025-10-06 11:52:15Z
*/
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..trust.audit import audit_hash
from ..policy.load import policy_for

router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    voice: str = "en_US_female"
    engine: str = "piper"  # piper | xtts | riva
    clone_ref: Optional[str] = None
    require_disclosure: bool = True
    jurisdiction: str = "EU"

@router.post("/synthesize")
def synth(req: TTSRequest) -> Dict[str, Any]:
    pol = policy_for(req.jurisdiction)
    if req.clone_ref and not pol.get("allow_cloning_with_consent", True):
        return {"error": "Cloning not permitted in this jurisdiction", "compliant": False}
    # Placeholder: route to engine adapter, return URL or bytes
    disclosure = "SYNTHETIC-VOICE" if req.require_disclosure or pol.get("require_disclosure", True) else ""
    return {
        "audio_ref": "file://example.wav",
        "engine": req.engine,
        "disclosure": disclosure,
        "audit_sha256": audit_hash(req.dict()),
        "compliant": True
    }
