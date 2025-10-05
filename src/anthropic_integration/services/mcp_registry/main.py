from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import time, hashlib

app = FastAPI(title="Belel MCP Registry", version="1.0")

LEDGER: Dict[str, dict] = {}

class ProofRecord(BaseModel):
    proof_hash: str
    signature: dict
    anchored: dict
    zkp: Optional[dict] = None
    proof_data: dict
    validation_issues: Optional[List[str]] = []
    fragments: Optional[List[str]] = []
    mcp: Optional[dict] = None

@app.post("/register")
def register_proof(record: ProofRecord):
    # Basic sanity
    if not record.proof_hash or not record.proof_data:
        raise HTTPException(400, "Invalid proof record")
    # Store in-memory (replace with DB in production)
    LEDGER[record.proof_hash] = record.dict()
    return {"status": "success", "id": record.proof_hash}

@app.get("/verify/{proof_hash}")
def verify_proof(proof_hash: str):
    rec = LEDGER.get(proof_hash)
    if not rec:
        raise HTTPException(404, "Not found")
    # Minimal integrity check: recompute hash of proof_data
    data = rec.get("proof_data", {})
    s = hashlib.sha256(
        __import__("json").dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "exists": True,
        "hash_matches": s == proof_hash,
        "stored": rec
    }
