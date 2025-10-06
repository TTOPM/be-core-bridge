# BELEL-MED — Sovereign Health AI Blueprint
**Timestamp:** 2025-10-06 11:18:36Z

## North-Star
A sovereign, evidence-locked health AI that ingests **all clinical modalities**, answers with **verifiable citations**, integrates **natively into workflows**, and operates with **zero-trust safety, regulatory-grade audit, and privacy-first learning**.

## System Overview — 4 Planes + 2 Edges
### A) Data Plane — Ingest & Normalize
- Connectors: FHIR R4/5 (EHR), HL7 v2, DICOM/PACS, LIS, pharmacy, claims, device SDKs (Apple HealthKit, Google Health Connect), wearables/telemetry, bedside monitors.
- Normalization: OMOP CDM mapping, units harmonization, timestamp alignment, de-identification (PHI tokenization).
- Quality: missingness/outlier reports, calibration profiles, lineage tracking.

### B) Knowledge Plane — Current & Ancient Medical Corpus
- **Sources**: WHO, NICE, CDC/ACIP, ESC/ACC, USPSTF, IDSA; PubMed/OA; Cochrane; licensed textbooks/formularies; **historical treatises** (flagged as historical, not prescriptive).
- **Hierarchical Knowledge Graph**: conditions ↔ findings ↔ labs ↔ meds ↔ pathways ↔ trials; causal/contraindication edges; regional variants; time-stamped versions.
- **Continuous Curation**: expert panel + automated scanners; retraction/errata watch; evidence freshness scoring.

### C) Model Plane — Multimodal & Verifiable
- **Foundation Models** (pluggable): text (clinician-tuned LLM), imaging (X-ray/CT/MRI, derm, retina, WSI), time-series (ECG/vitals/wearables), genomics/PGx, speech/vision.
- **Orchestrator**: retrieval-augmented reasoning with **Evidence Contracts** (mandatory citations, uncertainty, rationale, patient-fit).
- **Predictors**: early-warning (sepsis/AKI), readmission, longitudinal trajectories, dose calculators, DDI checks.

### D) Trust & Governance Plane
- **Policy**: region-aware rules; scope fences (draft-only actions); OPA policies.
- **Safety Rails**: contraindication sweeps; dosage sanity; pediatric/renal/hepatic guards.
- **Bias & Fairness Monitors**: subgroup calibration; drift detection; model cards with cohort stats.
- **Audit**: append-only ledger, data lineage, consent artifacts; periodic Merkle-root anchoring.
- **Privacy**: on-prem/VPC; federated learning; differential privacy; RBAC/ABAC; KMS/HSM.

### Edges
- **Clinician Edge**: SMART-on-FHIR EHR sidebar; PACS plug-ins; note drafting, order-set composer, patient message composer (sign-off required).
- **Patient Edge**: triage/chat, symptom checker, care-plan coach, adherence tracking; escalation thresholds defined.

## Signature Capabilities — Best of All Worlds
- **Evidence-Locked Answers**: inline citations with strength-of-evidence; “Why/What would change” explainers.
- **EHR-Native Workflow (Epic-grade integration)**: SOAP/discharge drafts; referral letters; coding suggestions; order-set composer aligned to local formulary.
- **Triage → Longitudinal Care (Cedars-Sinai/K Health DNA)**: red-flag detection; routing; daily check-ins; outcomes learning.
- **Multimodal Mastery**: radiology pre-reads with heatmaps; pathology WSI triage; ECG/telemetry; fall-risk video; pharmacogenomics.
- **Global/Local Intelligence**: region packs (UK/US/EU/CARICOM); low-resource modes (SMS/voice/offline).

## Truth Contract for Medical Claims
A structured JSON contract with summary, ranked differential, recommendations, contraindication check, uncertainty (aleatoric/epistemic), citations with evidence strength, patient-fit features, and audit hashes. **No claim without a source.**

## Safety & Regulatory Posture (Baked-In)
Human-in-the-loop; high-risk domains demand higher evidence; adversarial test suites; prospective validation; PMS and CAPA; model/data/IFU documentation.

## Tech Stack (Reference, Swappable)
FHIR server, OMOP ETL, Kafka pipelines; object store + vector DB; Triton/ONNX/TensorRT model runners; hybrid retrieval; OPA policy engine; SMART-on-FHIR UI; React Native patient app.

## Developer Surface
- `/v1/clinical/qa` — whole-chart Q&A (evidence contracts)
- `/v1/triage` — non-diagnostic triage with safety thresholds
- `/v1/radiology/analyze` — assistive pre-read with explainability
(See PRD `endpoints.yaml` and example schemas.)

## Data & Corpus Strategy (Legal & Complete)
Licensed + open sources; historical texts flagged; curator network; monthly KG snapshots; retraction propagation.

## Measurement & Proof
Time/note, alert precision/recall, med error intercepts, guideline concordance, 30-day readmission, ED bounce-backs, PROMs.

## Rollout Path — 90-Day Playbook
0–30: read-only ingest; view-only EHR; RAG sandbox.  
31–60: note drafting + citations; imaging/pathology shadow.  
61–90: limited order-set drafts; PGx pilots; metrics review → expand.

## Branding & Promise
**BELEL-MED** — sovereign, verifiable, clinician-first. Every suggestion: **traceable**, **explainable**, **region-aware**, and **safe by default**.
