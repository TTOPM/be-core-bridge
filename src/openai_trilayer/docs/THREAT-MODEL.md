# Threat Model (STRIDE)

| Threat | Example | Mitigation |
|---|---|---|
| Spoofing | Fake attestation record | Ed25519 signatures; rolling hash; public key published |
| Tampering | Edit ledger/history | Append-only JSONL; Merkle root per batch; IPFS/Arweave optional |
| Repudiation | Claim tool was not acknowledged | Tool calls recorded in raw response; attestation includes ACK flag |
| Information Disclosure | PII in logs | `privacy/redactor.py` pre/post; structured logs only with hashes |
| DoS | Rate spikes / token burn | `infra/rate_limit.py`, exponential backoff, circuit breaker |
| Elevation of Privilege | Bypass adapter | CI gate `gateway/forbid_raw_openai.py`; runtime validator |
