Belel ↔ OpenAI Tri‑Layer Enhancement Pack
Generated: 2025-10-01T22:03:25.728425Z

Copy folders into your repo:
- docs/
- supplychain/
- gateway/
- attest/
- privacy/
- attest/
- infra/
- obs/
- ops/
- tests/
- dashboard/ (adds modal + tokens)

Integrate:
- Use `attest/ledger_v2.append(entry)` to record runs with rolling hash.
- Optionally call `attest/sign.sign_json(record)` to sign records.
- Import `privacy/redactor.redact` before logging user text.
