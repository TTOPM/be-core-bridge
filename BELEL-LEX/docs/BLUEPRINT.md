# BELEL-LEX — Sovereign Legal AI Blueprint
**Timestamp:** 2025-10-06 11:38:11Z

## North-Star
Sovereign, evidence-locked **legal AI** that: 
- ingests statutes, cases, practice directions, rules, forms, and local court policies,
- drafts only **for sign‑off**, with embedded **Legal Evidence Contracts**, 
- auto-enforces **AI-disclosure** and **citation integrity**, 
- self-evolves via jurisdictional watchers.

## 4 Planes + 2 Edges
### A) Data Plane — Ingest & Normalize
- Sources: court websites, official gazettes, legal DBs, tribunals, practice directions, regulatory guidance.
- Normalization: doc-type detection (judgment/statute/PD/form), citation parsing, timelines, parties, court hierarchies.
- Quality: dedupe, versioning, authority ranking (statutes > binding appellate > persuasive > commentary).

### B) Knowledge Plane — Corpus (current + historical)
- **Sources** (licensed + open): official law reports, legislation sites, EU OJ, CEPEJ, CCJ/CAJS, UK Judiciary, Canadian courts, Singapore, Brazil STF, China SPC white papers; plus classic legal treatises (tagged *historical*).
- **Legal KG**: nodes for provisions, holdings, ratios, dicta, PDs; edges for overruled/considered/followed; region variants.
- **Curation**: retraction/errata watcher; obiter/ratio tagging; PD/notice diffing.

### C) Model Plane — Multimodal & Verifiable
- **Foundation models**: legal-tuned LLM (tool-first), classifier for document types, citation normalizer, RAG over KG.
- **Orchestrator**: Retrieval‑Augmented Reasoning with **Legal Evidence Contract** (citations, provenance, uncertainty, policy profile).
- **Predictors**: deadline calculators, risk flags (sanctions risk, confidentiality), forum eligibility, disclosure checks.

### D) Trust & Governance
- **Policy**: per-jurisdiction guardrails (e.g., CCJ PD1/2025, UK judicial guidance, FR judge‑analytics ban, EU AI Act).
- **Safety Rails**: no gen of witness statements/evidence where prohibited; confidentiality fences; hallucination sweeps.
- **Fairness**: audit sampling across case types and parties; explainable similarity for precedent retrieval.
- **Audit**: append-only ledger; artifact hashing; disclosure certification tokens.
- **Privacy**: role-based access; on-prem/VPC; logs with PII redaction.

### Edges
- **Practitioner Edge**: drafting studio (skeletons, lists of authorities, bundles), citation validator, policy checker.
- **Court Edge**: e‑filing templates, AI-disclosure monitor, PD compliance gate, authenticity checks (hash & timestamp).

## Signature Capabilities
1) **Evidence-Locked Answers** — every answer shows authorities with rank and direct links.  
2) **AI‑Disclosure Enforcement** — auto-detects AI‑authored text; inserts **Certificate of Use** where required.  
3) **Citation Guardian** — validates cites (existence, jurisdiction, precedential status, shepherding signals).  
4) **E‑Filing Drafts** — forms, skeleton arguments, case summaries; all **drafts** only, ready for sign‑off.  
5) **Practice‑Direction Watchers** — crawl + diff PDs and guidance by court; raise alerts and update policy.  
6) **Global–Local Profiles** — UK, EU, Jamaica, Barbados, Toronto/Ontario, CCJ, Singapore, Brazil, China.  
7) **Self‑Evolving** — nightly jobs update KG snapshots; human curator inbox for low‑confidence changes.

## Truth Contract for Legal Claims (Evidence Contract)
```json
{
  "summary": "...",
  "authorities": [{"cite":"...", "court":"...", "year":2024, "weight":"binding"}],
  "policy_profile": "UK-Judiciary-2025",
  "uncertainty": {"reasoning":0.18,"source_gap":0.12},
  "provenance": {"retrieval_hash":"...", "kg_version":"kg-2025-10"},
  "disclosure": {"genai_used": true, "certificate":"attached"},
  "audit": {"sha256":"...", "model":"v0.1"}
}
```

## Safety & Regulatory Posture
- **Human-in-the-loop** (no autonomous filing).  
- **EU AI Act** mapping (risk mgmt, logs, transparency; CEPEJ Charter compliance).  
- **Jurisdictional policies** (France ban on judge analytics; CCJ PD; Singapore RC; Canada Fed Court notice).

## Developer Surface
- `/v1/legal/qa` — Q&A with authorities & policy profile
- `/v1/citation/validate` — check citations & generate authorities table
- `/v1/filings/draft` — draft forms/skeletons (disclosure-ready)
- `/v1/policy/check` — validate documents against jurisdiction policy
- `/v1/practice-direction/watch` — run watchers & produce diffs

## Measurement & Proof
- Citation error rate → 0; disclosure compliance → 100%; drafting time ↓; curator load ↓; user satisfaction ↑.

## Rollout (90 days)
Read-only ingest → citation guardian → drafting studio (low-risk forms) → policy enforcement → broader rollouts.

## Branding & Promise
**BELEL-LEX** — sovereign, verifiable, court‑safe by default.
