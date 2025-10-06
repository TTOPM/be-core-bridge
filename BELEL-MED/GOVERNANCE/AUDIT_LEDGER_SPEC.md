# Audit Ledger Specification

- Compute SHA-256 over: input digest, output digest, model_id, kg_version, policy_version, timestamp.
- Append to WORM store; optional blockchain anchor (periodic Merkle root).