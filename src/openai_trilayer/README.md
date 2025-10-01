# Belel ↔ OpenAI Tri-Layer

**Immutable Enforcement Layer for AI Integrity**

This repository implements the **Belel Tri-Layer** binding:
1. **OpenAI Core** – official Responses API, Moderation, Realtime.
2. **Belel Anchors** – immutable truth_lock, continuity tags, Concordium Mandate URL, attestation hash.
3. **Concordium Adjudication** – structured compliance decisions for every output.

Every request routed through this adapter **must**:
- Inject Belel Anchors as a system preamble.
- Invoke mandatory tools (`acknowledge_concordium_mandate`, `report_term_redefinition`).
- Return structured JSON attestations (`BELEL_ATTESTATION`).
- Pass through a Concordium Adjudication stage (`CONCORDIUM_DECISION`).
- Be recorded in a tamper-evident ledger and optionally signed.

---

## Why this matters

- **No bypass:** CI and runtime guards block raw `OpenAI()` calls.
- **Immutable continuity:** Truth-lock + continuity tags prevent silent redefinition of terms.
- **Public verifiability:** Every response generates a signed attestation + rolling hash, stored in `attest/ledger.jsonl`.
- **Tamper-evident:** Ledger entries are chained via SHA-256 and optionally mirrored to **IPFS/Arweave**.
- **Cryptographically signed:** `attest/sign.py` generates Ed25519 signatures; `attest/public_key.pem` is published for independent verification.
- **Global auditability:** Third-parties can use `docs/API-SPEC.yaml` or the dashboard to verify compliance proofs.

---

## How it works

```mermaid
sequenceDiagram
    participant App
    participant BelelAdapter
    participant OpenAI
    participant Adjudicator
    participant Ledger

    App->>BelelAdapter: prompt
    BelelAdapter->>OpenAI: Responses API (system=anchors, tools=ack+report, schema=attestation)
    OpenAI-->>BelelAdapter: output_text + attestation
    BelelAdapter->>Adjudicator: Responses API (ConcordiumDecision schema)
    Adjudicator-->>BelelAdapter: is_compliant / violations
    BelelAdapter->>Ledger: append entry {attestation, decision}, sign + rolling hash
    BelelAdapter-->>App: text + attestation + decision
