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
from fastapi import FastAPI
from .routers import clinical, triage, radiology

app = FastAPI(title="BELEL-MED API", version="0.1.0")

app.include_router(clinical.router, prefix="/v1/clinical", tags=["clinical"])
app.include_router(triage.router, prefix="/v1", tags=["triage"])
app.include_router(radiology.router, prefix="/v1/radiology", tags=["radiology"])

@app.get("/healthz")
def healthz():
    return {"ok": True}
