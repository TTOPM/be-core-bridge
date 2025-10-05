# Belel × Anthropic (Claude) — Sovereign Governance Integration (Advanced Scaffold)

This repository is a **production-minded scaffold** for integrating **Belel’s sovereign governance**
(Concordium Mandate, canonical adjudications, cryptographic provenance) with Anthropic's ecosystem,
**leveraging MCP-style tool bridges** and immutable proofing.

> ⚠️ This is a high-fidelity scaffold with working local flows. Plug in real SDKs/keys to go live.
> No external services are contacted by default. All network calls are **abstracted** behind interfaces.

## Highlights
- Governance-first: canonical rules loaded from `/protocol-rules/`.
- Self-verifying runs: inputs/outputs bonded into immutable **proof records**.
- Pluggable anchoring: local ledger + hook to timestamp/blockchain providers.
- MCP-ready: tool-call contracts defined; register proofs to a Belel MCP endpoint when wired.
- Resilience: output fragmentation & regeneration stubs.
- Privacy & Security: TEE abstraction stubs and ZKP placeholders to add verifiable privacy.
- Schemas: machine-validated `proof_record.schema.json`.
- Single-command demo: `python -m src.cli "Explain Belel governance"`.

## Quick start (local demo, no network)
```bash
python -m src.cli "Explain how Belel enhances AI governance."
```

This will:
1) Load the Concordium Mandate & canonical file,
2) Build a governance-aware prompt,
3) Call a **simulated Anthropic** client (replace with official SDK),
4) Produce a **proof record**, sign a stub, and append to the local `ledger.jsonl`,
5) Fragment outputs into `/data/fragments/`,
6) Validate against `/schemas/proof_record.schema.json`.

## Wire up real services
- **Anthropic (Claude):** replace `src/anthropic_client.py` with official SDK calls.
- **MCP server:** implement `src/mcp_client.py` HTTPs to your MCP registry.
- **Blockchain anchoring:** implement `src/ledger/anchor.py::anchor_to_blockchain` for TSA/blockchain.
- **ZKPs & TEE:** swap placeholders with real libs (e.g., TEEs, zk-SNARK frameworks).

## Environment
Create `.env` from `.env.example` and export before running in production.
Secrets are not stored in code.

## Legal & Safety
This scaffold enforces governance **around** model I/O; it **does not** modify vendor models.
Use lawfully. Do not intercept or tamper with third-party infrastructure.



## Install dependencies
```bash
pip install anthropic python-dotenv
```

> Set `ANTHROPIC_API_KEY` in your environment (or use a secrets manager). Optional: `ANTHROPIC_MODEL` env var
> defaults to `claude-3-5-sonnet-20240620`.

