# Threat Model (Minimum Viable)

## Goals
- Preserve integrity and auditability of model IO under Belel governance.
- Prevent unauthorized alteration of proofs and audit trail.

## Key Threats & Mitigations
- **Proof tampering** → Ed25519 signatures + external anchoring.
- **Registry compromise** → Immutable anchoring + off-site SBOM & logs.
- **Key exposure** → Use HSM/KMS in production; never commit secrets.
- **Supply-chain** → SBOM, Dependabot/Renovate, CI scans (bandit/safety), provenance attestation.
- **Replay/forgery** → Nonces/timestamps in proof_data; verification endpoints recompute hash.
