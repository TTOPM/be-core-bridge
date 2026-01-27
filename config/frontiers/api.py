"""
Frontiers API Service
=====================

This module exposes the frontiers meta-orchestrator through a simple FastAPI
interface. It defines a single endpoint `/guide` that accepts a JSON body
containing a query and returns the structured guidance response.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from src.frontiers.meta.code_above_all_codes import CodeAboveAllCodes


app = FastAPI(title="Belel Frontiers: Code Above All Codes", version="0.1.0")
meta = CodeAboveAllCodes()


class GuideRequest(BaseModel):
    query: str


@app.post("/guide")
def guide(req: GuideRequest):
    return meta.guide(req.query)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8787)