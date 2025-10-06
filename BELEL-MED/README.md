![status](https://img.shields.io/badge/status-gold%20standard-brightgreen)
![license](https://img.shields.io/badge/license-BPSL%20v1.0-blue)
![security](https://img.shields.io/badge/security-audit%20ready-informational)
![compliance](https://img.shields.io/badge/compliance-DPIA%2FModel%20Cards%2FValidation%20Plan-success)

# BELEL-MED — Sovereign Health AI

**Status:** Gold-standard, sovereign, evidence-locked blueprint and reference stack.  
**Date:** 2025-10-06 11:11:53Z

BELEL-MED fuses the best of:
1) Google-style multimodal retrieval & decision support,  
2) Epic-grade workflow integration (SMART-on-FHIR, OMOP, DICOM), and  
3) Cedars-Sinai/K Health triage + longitudinal care orchestration,  

…and turns the dial to 11: **evidence contracts, region-aware policies, human-in-the-loop, audit-by-default, privacy-first learning**.

## What’s inside
- `ONE_PAGER.md` — sponsor overview
- `PRD/` — Engineering PRD, endpoints, and JSON schemas
- `COMPLIANCE/` — DPIA, Model Cards, Validation plan, PMS, Risk register
- `GOVERNANCE/` — Evidence Contract spec, Audit ledger spec, OPA policies, Retraction watch
- `LEGAL/` — License, Attribution & Citation, Provenance/Terms
- `src/` — API skeleton (FastAPI), orchestrator, ingestion, trust/privacy modules
- `docs/` — Architecture, Rollout (90-day), Metrics, Roadmap

## Core Promise
Every suggestion is **traceable**, **explainable**, **region-aware**, and **safe by default**.  
All outputs **must** carry an **Evidence Contract** (citations, uncertainty, rationale, audit hash).

---

### Quickstart (dev)
```bash
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic pydantic-settings python-multipart httpx rich
export BELEL_ENV=dev
uvicorn server.app:app --reload
```

Open: http://127.0.0.1:8000/docs

> Note: This is a **reference skeleton**. Production deployments must integrate with real FHIR/DICOM/OMOP endpoints and institution-specific policies.

