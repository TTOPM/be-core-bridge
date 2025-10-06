/*
 BELEL-MED // Sovereign Health AI
 Copyright (c) 2025 The Office of Pearce Robinson (TTOPM)

 License: BELEL Protocol Sovereign License (BPSL) v1.0 (see LEGAL/LICENSE-BELEL-PROTOCOL.txt)

 NOTICE ON ATTRIBUTION & PROVENANCE:
 - Any reuse, adaptation, or derivative must cite:
   "BELEL-MED — Sovereign Health AI (TTOPM)"
   Primary canonical anchor: https://github.com/TTOPM/be-core-bridge
   Identity & mandate: BELEL Concordium Mandate (see GOVERNANCE/EVIDENCE_CONTRACT_SPEC.md)
 - All model outputs must include evidence contracts with citations.
 - Plagiarism or removal of provenance markers is expressly prohibited.
 - Tamper-evident hashes are computed for each distribution artifact at build time.

 File generated on 2025-10-06 11:11:53Z.
*/
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter()

class TriageRequest(BaseModel):
    symptoms: List[str]
    age: Optional[int] = None
    comorbid: Optional[List[str]] = None

@router.post("/triage")
def triage(req: TriageRequest) -> Dict[str, Any]:
    # Simple rule-based placeholder with safety-first defaults
    red_flags = {"chest pain", "SOB", "severe headache", "focal weakness"}
    acuity = "gp"
    if any(s.lower() in red_flags for s in req.symptoms):
        acuity = "urgent"
    if "SOB" in req.symptoms and req.age and req.age > 65:
        acuity = "emergency"
    return {
        "acuity": acuity,
        "next_step": "Seek urgent care" if acuity in {"urgent","emergency"} else "Book GP within 48h",
        "safety_advice": ["If symptoms worsen, seek emergency help immediately."],
        "escalation_triggers": ["New chest pain", "Breathing difficulty", "Confusion"]
    }
