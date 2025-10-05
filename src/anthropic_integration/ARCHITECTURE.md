# Architecture Overview

- **Governance Envelope** around vendor models (Anthropic Claude), not weight tampering.
- **Proof Bonding**: input+prompt+output → `proof_hash` (+ Ed25519 signature, ZKP placeholder).
- **Anchoring**: local ledger + pluggable TSA/blockchain hook.
- **MCP Registry**: FastAPI service for `/register` and `/verify` proof records.
- **Tracing**: OpenTelemetry hooks (OTLP exporter ready).
- **Resilience**: Fragmentation & regeneration stubs.
- **Supply Chain**: CI builds, SBOM via Syft, ready for signing (cosign) and provenance (SLSA).

