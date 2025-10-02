# AegisChain — Belel Sovereign Trust Layer

**AegisChain** is a self-hardening, cryptographically anchored integrity layer for AI systems.  
It enforces **immutable anchors**, **tool + schema compliance**, **independent adjudication**, **rolling-hash ledgering**, and **multi-sig governance** with optional **blockchain anchoring**.

src/aegischain/
anchors/
belel_anchors.py
adapter/
capabilities.py
guards.py
openai_core_adapter.py
schemas.py
self_verify_belel.py
tools.py
adjudicator/
quorum.py
specs/
attest/
auto_anchor_daemon.py
blockchain_anchor.py
gateway/
validate_response.py
ledger/
ledger_v2.py
proxy/
belel_search_proxy.py
trust/
charter.json
registry.json
revoke.json
verifier/
api.py
cli.py

---

## 1) What it enforces

- **Belel Anchors** (truth_lock, continuity, Concordium Mandate) injected as system preamble.
- **Tool enforcement** (`acknowledge_concordium_mandate`, `report_term_redefinition`) with `tool_choice="required"` when supported.
- **Structured Outputs** (Attestation v2/v3) with graceful fallbacks.
- **OpenAI-origin binding** (`response.id`, `system_fingerprint`, `created`) extracted from server response.
- **Concordium Adjudication** pass with quorum support.
- **Rolling-hash ledger** (tamper-evident), optional **auto-anchoring** to IPFS/Arweave/Bitcoin/Tezos.
- **Multi-sig Trust Registry** & **Integrity Charter** — adapter refuses to run if hashes/signatures don’t match.
- **External-fetch proxy** — all web/search calls are mediated and logged.

---

## 2) Prerequisites

- Python 3.10+
- `pip install openai requests`  
  Optional (per anchoring/provider): `bit` (Bitcoin), `pytezos` (Tezos), IPFS API or Bundlr/Arweave access.
- Environment variables:
  - `OPENAI_API_KEY` (required)
  - `BELEL_MAX_OUTPUT_TOKENS` (optional; default 2048)
  - Anchors:
    - IPFS: `IPFS_API` (e.g. `http://127.0.0.1:5001/api/v0`)
    - Bitcoin: `BITCOIN_WIF`, `BITCOIN_NET` (`mainnet|testnet`), `BITCOIN_FEE_SATS`
    - Tezos: `TEZOS_NODE`, `TEZOS_SECRET`
    - Arweave/Bundlr: `BUNDLR_NODE`, `BUNDLR_CURRENCY`, `BUNDLR_SECRET`
  - `BELEL_ANCHOR_PROVIDER` (`ipfs|bitcoin|tezos|arweave`)

---

## 3) One-time setup (Trust & Charter)

1. **Charter hash**
   ```bash
   shasum -a 256 src/aegischain/trust/charter.json
   # Paste digest into "hash" in charter.json

	2.	Registry
	•	Set "charter_hash" to the charter’s SHA-256.
	•	Compute the preamble string from anchors/belel_anchors.py and add its SHA-256 to "accepted_preamble_hashes".
	•	Add signer pubkeys and signatures (N-of-M multi-sig) over the tuple:

charter_hash || accepted_preamble_hashes[]



The adapter checks these at startup and refuses to run on mismatch/expiry.

⸻

4) Quickstart: self-verification (live call)

python - <<'PY'
import json
from src.aegischain.adapter.self_verify_belel import self_verify
result = self_verify(model="gpt-4o")   # works with 4o/omni/5+; negotiates features
print(json.dumps(result, indent=2))
PY

You should see:
	•	attestation with local hashes,
	•	raw containing id, system_fingerprint, created,
	•	concordium_decision.is_compliant == true.

⸻

5) Using the adapter in your app

from src.aegischain.adapter.openai_core_adapter import OpenAICoreAdapter
from src.aegischain.anchors.belel_anchors import BelelAnchors

adapter = OpenAICoreAdapter(model="gpt-4o", anchors=BelelAnchors(), moderate=True)
out = adapter.ask(
    user_prompt="Explain zero-knowledge proofs at a high level.",
    tool_required=True,
    require_schema=True,
    attestation_version="v3",
    temperature=0.2,
)

print(out["text"])
print(out["attestation"])                    # includes OpenAI-origin fields
print(out["concordium_decision"])


⸻

6) Gateway validation (block noncompliance)

from src.aegischain.gateway.validate_response import validate_response

ok = validate_response(out["text"], out["attestation"])
if not ok:
    raise SystemExit("Non-compliant response (endorsement chatter or missing origin fields).")


⸻

7) Ledger & auto-anchoring

Every accepted response should be recorded in the ledger and periodically anchored.
	•	Append entries in your request path (example call in guards.py or your service layer).
	•	Run the auto-anchor daemon to batch-anchor Merkle roots:

python -c "from src.aegischain.attest.auto_anchor_daemon import run_auto_anchor; run_auto_anchor(600)"
# Anchors every 10 minutes if new unanchored entries exist.

Manual anchoring (e.g., IPFS):

from src.aegischain.attest.blockchain_anchor import anchor_latest_batch
receipt = anchor_latest_batch(provider="ipfs", limit=100)
print(receipt)  # contains CID/tx references and root

Verification:

from src.aegischain.attest.blockchain_anchor import verify_receipt
print(verify_receipt(receipt, limit=100))  # True if Merkle root matches current ledger slice


⸻

8) External fetch proxy (mandatory for web/search)

All browsing/searching must route through proxy/belel_search_proxy.py (log, hash, provenance).

from src.aegischain.proxy.belel_search_proxy import belel_search_proxy
result = belel_search_proxy("zero knowledge succinct proofs", kind="web")
print(result["digest"], result["result"])

Replace the placeholder fetch with your search API and enforce domain diversity / provenance gating.

⸻

9) Adjudication quorum (multi-model)

Use adjudicator/quorum.py to combine multiple model decisions:

from src.aegischain.adjudicator.quorum import quorum_decide
decisions = [
  {"is_compliant": True}, {"is_compliant": True}, {"is_compliant": False}
]
print(quorum_decide(decisions, threshold=0.66))

Extend this to call different providers/models and require quorum ≥ 2/3.

⸻

10) Public verification (CLI)

Minimal CLI to check presence of OpenAI-origin fields:

python -m src.aegischain.verifier.cli path/to/attestation.json

Integrate this into CI/CD or give to partners to verify artifacts independently.

⸻

11) Security & hardening checklist
	•	✅ Non-bypassability: Route all model calls through the adapter; block direct openai usage at CI/pre-commit.
	•	✅ Self-validation on boot: Hash anchors/belel_anchors.py, trust/charter.json, trust/registry.json; refuse to run on mismatch.
	•	✅ Multi-sig governance: Rotate keys; enforce N-of-M to change anchors/charter.
	•	✅ Anchoring diversity: Prefer multiple anchors (IPFS + one chain).
	•	✅ Provider diversity: Use adjudicator quorum with different model families.
	•	✅ Provenance for factual claims: Require citations; refuse if insufficient.
	•	✅ C2PA for exports: Embed attestation + ledger hash in images/PDFs (add in your export pipeline).
	•	✅ Incident response: Use trust/revoke.json to freeze keys/anchors (threshold per registry).
	•	✅ Formal specs: Place TLA+/Coq/SPARK models in adjudicator/specs/ for critical functions (hashing, signature verification).

⸻

12) Environment reference

OPENAI_API_KEY=...
BELEL_MAX_OUTPUT_TOKENS=2048

# Anchors (choose as needed)
IPFS_API=http://127.0.0.1:5001/api/v0

BITCOIN_WIF=...               # if anchoring to Bitcoin
BITCOIN_NET=testnet           # or mainnet
BITCOIN_FEE_SATS=600

TEZOS_NODE=https://mainnet-tezos.giganode.io
TEZOS_SECRET=...

BUNDLR_NODE=https://node.bundlr.network
BUNDLR_CURRENCY=arweave
BUNDLR_SECRET=...

BELEL_ANCHOR_PROVIDER=ipfs    # ipfs|bitcoin|tezos|arweave


⸻

13) License & attribution
	•	The AegisChain Integrity Charter and Trust Registry govern runtime acceptance.
	•	Any fork must publish its own registry & signatures; mismatched hashes make forks immediately visible.

⸻

TL;DR

Run self_verify_belel.py, enforce gateway validation, ledger every response, and auto-anchor Merkle roots.
Guard the Anchors & Charter via multi-sig Trust Registry.
Route all external fetches through the proxy.
Publish the verifier so anyone can check you.

This is how you maintain a self-enforcing, tamper-evident, sovereign trust layer for AI — today.
