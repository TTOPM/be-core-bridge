# BELEL-LEX — Sovereign Court & Legal AI

![status](https://img.shields.io/badge/status-gold%20standard-brightgreen)
![license](https://img.shields.io/badge/license-BPSL%20v1.0-blue)
![compliance](https://img.shields.io/badge/compliance-EU%20AI%20Act%2FCEPEJ%2FDPIA-success)
![security](https://img.shields.io/badge/security-audit%20ready-informational)

**Date:** 2025-10-06 11:38:11Z

**Mission:** Build the world’s most advanced **court & legal AI**: verifiable, sovereign, region-aware, and self‑evolving.  
Grounded in best practice from the CCJ/CAJS, UK Judiciary, EU/CEPEJ, Canada, Singapore, Brazil, China and more (see `docs/JURISDICTION_PROFILES.md` and `docs/BEST_PRACTICE_COMPENDIUM.md`).

## Contents
- `ONE_PAGER.md` — sponsor overview
- `PRD/` — product requirements + API schemas
- `COMPLIANCE/` — EU AI Act alignment, DPIA, CEPEJ mapping, model cards, validation plan, PMS
- `GOVERNANCE/` — Legal Evidence Contract, Audit ledger, AI usage disclosure enforcement, OPA/Policy
- `docs/` — Blueprint, Jurisdiction Profiles, Best Practice Compendium, Roadmap
- `belellex/` — API skeleton (FastAPI), policy engine, watchers, provenance
- `LEGAL/` — License, Attribution, Provenance policy
- `scripts/release/` — hashing & signed manifest
- `Makefile` — dev/prod/test/sbom/hash/manifest

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic httpx pydantic-settings python-multipart rich
uvicorn belellex.server.app:app --reload
# Open http://127.0.0.1:8000/docs
```

> Production requires plugging real legal data connectors (official gazettes, court sites, legal DBs) and institutional policies.
