"""
BELEL-MED — Sovereign Health AI
Copyright (c) 2025 The Office of Pearce Robinson (TTOPM)

License: BELEL Protocol Sovereign License (BPSL) v1.0
(see LEGAL/LICENSE-BELEL-PROTOCOL.txt)

NOTICE ON ATTRIBUTION & PROVENANCE:
- Any reuse, adaptation, or derivative must cite:
  "BELEL-MED — Sovereign Health AI (TTOPM)"
- Canonical anchor: https://github.com/TTOPM/be-core-bridge
- Identity & mandate: BELEL Concordium Mandate (see GOVERNANCE/EVIDENCE_CONTRACT_SPEC.md)
- All outputs should include evidence contracts with citations.
- Removal of provenance markers is prohibited.
- Tamper-evident hashes may be computed at build time.

File generated on 2025-10-06 11:11:53Z (updated for Python validity & hardening).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# --- audit_hash import (hardened) --------------------------------------------
# CodeQL/CI can fail analysis when imports are broken by path layout. This
# fallback keeps the module importable even if the audit subsystem is not
# present in a minimal test environment.
try:
    from ..trust.audit import audit_hash  # type: ignore
except Exception:
    def audit_hash(_: Any) -> str:
        # Safe deterministic-ish fallback (non-cryptographic).
        return "audit_hash_unavailable"


# --- router -------------------------------------------------------------------
router = APIRouter(prefix="/clinical", tags=["clinical-qa"])

# --- models -------------------------------------------------------------------

class Scope(BaseModel):
    """
    Query scope constraints for the clinical QA retrieval/orchestration layer.
    """
    last_days: Optional[int] = Field(
        default=None,
        ge=0,
        le=3650,
        description="Limit context to events within the last N days."
    )
    modalities: Optional[List[str]] = Field(
        default=None,
        description="Modalities to include (e.g. labs, meds, notes, imaging)."
    )


class ClinicalQARequest(BaseModel):
    """
    Input contract for clinical evidence-locked QA.
    """
    patient_id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=3, max_length=5000)
    scope: Optional[Scope] = None
    region: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional region code to select guideline hierarchy (e.g. UK)."
    )


class RankedCondition(BaseModel):
    condition: str = Field(..., min_length=1, max_length=256)
    p: float = Field(..., ge=0.0, le=1.0, description="Calibrated probability estimate.")


class EvidenceItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=256)
    type: Literal["guideline", "trial", "systematic_review", "observational", "expert_consensus", "other"] = "other"
    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    strength: Optional[str] = Field(default=None, max_length=32)
    url: Optional[str] = Field(default=None, max_length=2048)


class UncertaintyBlock(BaseModel):
    aleatoric: float = Field(..., ge=0.0, le=1.0)
    epistemic: float = Field(..., ge=0.0, le=1.0)


class AuditBlock(BaseModel):
    data_hash: str
    model_version: str
    kg_version: str
    request_id: str
    timestamp_utc: str


class ClinicalQAResponse(BaseModel):
    summary: str
    ddx_ranked: List[RankedCondition]
    recommendations: List[str]
    contraindications_checked: bool
    uncertainty: UncertaintyBlock
    evidence: List[EvidenceItem]
    patient_fit: List[str]
    audit: AuditBlock


# --- helpers ------------------------------------------------------------------

def _dump_model(obj: BaseModel) -> Dict[str, Any]:
    """
    Support both Pydantic v2 (.model_dump) and v1 (.dict).
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj.dict()  # type: ignore[attr-defined]


# --- endpoint -----------------------------------------------------------------

@router.post(
    "/qa",
    response_model=ClinicalQAResponse,
    status_code=status.HTTP_200_OK,
)
async def clinical_qa(req: ClinicalQARequest) -> ClinicalQAResponse:
    """
    Evidence-locked clinical QA endpoint.

    Current behavior: prototype response with an audit hash of the request payload.
    Future behavior: orchestrator integration (retrieval, guideline hierarchy selection,
    contraindication checks, citations, and evidence contracts).
    """
    try:
        request_id = str(uuid4())
        now_utc = datetime.now(timezone.utc).isoformat()

        # Base prototype payload (replace with orchestrator output later)
        ans = ClinicalQAResponse(
            summary="Prototype: evidence-locked answer would appear here.",
            ddx_ranked=[RankedCondition(condition="Example", p=0.5)],
            recommendations=["Example recommendation"],
            contraindications_checked=True,
            uncertainty=UncertaintyBlock(aleatoric=0.2, epistemic=0.3),
            evidence=[
                EvidenceItem(
                    id="NICE-Example",
                    type="guideline",
                    year=2024,
                    strength="A",
                    url="https://www.nice.org.uk/",
                )
            ],
            patient_fit=["Example feature"],
            audit=AuditBlock(
                data_hash="TBD",
                model_version="v0.1",
                kg_version="kg-2025-10",
                request_id=request_id,
                timestamp_utc=now_utc,
            ),
        )

        # Audit hash of the request payload (stable serialization)
        payload = _dump_model(req)
        ans.audit.data_hash = audit_hash(payload)

        return ans

    except HTTPException:
        raise
    except Exception as e:
        # Keep errors deterministic, non-leaky, and API-consumable.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clinical QA failed to process request.",
        ) from e
