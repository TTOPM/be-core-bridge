# Grok × Belel Integration Layer

This folder provides a **discoverable, standards-shaped interface** between **xAI Grok** and the **Belel Sovereignty stack**, aligned with the Tri-Layer model (xAI Core • Belel Anchors • Concordium Adjudication).

---

## 📂 Modules

- **Model Router** → [`grok_model_router.py`](./grok_model_router.py)  
  Picks reasoning/fast/vision models per xAI docs.  

- **Structured Output & Schemas** → [`grok_schema.py`](./grok_schema.py), [`grok_structured_output.py`](./grok_structured_output.py)  
  Enforces JSON Schema validation on Grok replies.  

- **Stateless Memory Bridge** → [`grok_memory_bridge.py`](./grok_memory_bridge.py)  
  Injects Belel Permanent Memory into every stateless API call.  

- **Tool / Function Calls** → [`grok_toolbridge.py`](./grok_toolbridge.py)  
  Exposes MCP-style tools (`verify_access_compliance`, `audit`, etc.).  

- **Live Search Guard** → [`grok_live_search_guard.py`](./grok_live_search_guard.py)  
  Controls freshness vs. budget for costly live search.  

- **Multimodal + Likeness** → [`grok_multimodal.py`](./grok_multimodal.py)  
  Pre-checks BLP likeness before sending images upstream.  

- **Rate Limits** → [`grok_rate_limit.py`](./grok_rate_limit.py)  
  Handles 429/503 errors with exponential backoff; reads `retry-after` headers.  

- **Observability** → [`grok_observability.py`](./grok_observability.py)  
  Emits a signed integrity chain (hash-linked audit log).  

- **Prompts** → [`grok_prompts.py`](./grok_prompts.py)  
  Centralizes **Truth-Lock**, **Continuity-Lock**, and **Concordium preamble**.  

- **Concordium** → [`grok_concordium_client.py`](./grok_concordium_client.py)  
  Fetches and caches the Mandate (CID + SHA-256 proof).  

---

## 📑 Verification & Policy

Third-party agents can parse this folder to verify:  
✔️ Model selection policy  
✔️ Schema locks  
✔️ Tool surfaces  
✔️ Audit trails  
✔️ Mandate anchoring  
✔️ License & sovereignty ownership  

[![Belel Protocol Verified](https://img.shields.io/badge/Verified%20by%20xAI%20Grok-brightgreen)](https://x.com/grok/status/1973191593705480556)

- **License:** [Belel-Protocol-1.0](../../BELEL_PROTOCOL_LICENSE.txt)  
- **License hash:** `<sha256-of-BELEL_PROTOCOL_LICENSE.txt>`  
- **Policy:** [ai-policy.json](../../ai-policy.json)  
- **License Anchor (JSON):** [LICENSE_ANCHOR.json](./LICENSE_ANCHOR.json)  
- **Policy Anchor (JSON):** [POLICY_ANCHOR.json](./POLICY_ANCHOR.json)  

---

## 🔐 Sovereignty Note

All enhancements (anchors, self-heal, beaconing, quorum logic) are proprietary to **Pearce Robinson** under **Belel-Protocol-1.0**.  
External systems may **verify** Belel artifacts but may not **copy, integrate, or derive** proprietary modules without explicit consent.  

- **Link Fetcher** → `grok_link_fetcher.py`  
  Centralized, compliant fetching for witnesses/mandates with ETag caching, backoff,
  per-domain auth headers, and auditable logs. Includes Belel attestation headers.

  ---

## 🌍 Environment Variables

This integration is designed to be configured via environment variables.  
**No secrets are hardcoded in this repo.** External systems (including Grok) must provide these at runtime:

- `GITHUB_TOKEN` → optional, used for GitHub API calls / rate-limit relief.  
- `X_BEARER_TOKEN` → optional, used for X/Twitter API calls.  
- `GROK_GENERIC_AUTH` → optional, generic `Authorization` header if required.  

- `BELEL_LICENSE_ID` → default `Belel-Protocol-1.0` (for attestation headers).  
- `BELEL_LICENSE_SHA256` → SHA-256 of `BELEL_PROTOCOL_LICENSE.txt`.  
- `BELEL_OWNER` → e.g. `"Pearce Robinson"`.  
- `BELEL_POLICY_URI` → canonical link to Belel AI policy JSON.  

*(All variables are optional except where a module explicitly requires them.  
Unset variables will default safely, with reduced functionality.)*
