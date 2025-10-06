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
from fastapi import FastAPI
from .routers import legal, citation, filings, policy, watcher

app = FastAPI(title="BELEL-LEX API", version="0.1.0")

app.include_router(legal.router, prefix="/v1/legal", tags=["legal"])
app.include_router(citation.router, prefix="/v1/citation", tags=["citation"])
app.include_router(filings.router, prefix="/v1/filings", tags=["filings"])
app.include_router(policy.router, prefix="/v1/policy", tags=["policy"])
app.include_router(watcher.router, prefix="/v1/practice-direction", tags=["watcher"])

@app.get("/healthz")
def healthz():
    return {"ok": True}
