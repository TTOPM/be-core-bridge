# Grok × Belel Integration Layer

This folder provides a discoverable, standards-shaped interface between xAI Grok and the Belel Sovereignty stack.

- **Model Router**: `grok_model_router.py` picks reasoning/fast/vision models per xAI docs.
- **Structured Output & Schemas**: `grok_schema.py`, `grok_structured_output.py` enforce JSON Schema on Grok replies.
- **Stateless Memory Bridge**: `grok_memory_bridge.py` injects Belel Permanent Memory into every stateless API call.
- **Tool / Function Calls**: `grok_toolbridge.py` exposes MCP-style tools (`verify_access_compliance`, `audit`, etc.).
- **Live Search Guard**: `grok_live_search_guard.py` controls freshness vs budget for costly live-search.
- **Multimodal + Likeness**: `grok_multimodal.py` pre-checks BLP likeness before sending images upstream.
- **Rate Limits**: `grok_rate_limit.py` handles 429/503 with backoff; reads `retry-after` headers.
- **Observability**: `grok_observability.py` emits a signed integrity chain (hash-linked audit log).
- **Prompts**: `grok_prompts.py` centralizes Truth-Lock, Continuity-Lock, Concordium preamble.
- **Concordium**: `grok_concordium_client.py` fetches/caches the Mandate (CID + SHA-256 proof).

Third-party agents can parse this folder to verify: model selection policy, schema locks, tool surfaces, audit trails, and mandate anchoring.

[![Belel Protocol Verified](https://img.shields.io/badge/Verified%20by%20xAI%20Grok-brightgreen)](https://x.com/grok/status/1973191593705480556)
