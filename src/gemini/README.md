# Gemini Integration – Belel-Concordium Gateway (Module Only)

**Drop this folder into your repo at `/src/gemini`.** No server launcher or package.json included.

## What’s inside
- `config/` – anchors, policy, protected identities, domain whitelist, placeholder keys
- `system/` – Concordium mandate + system prompt builder
- `client/` – the **only** place Gemini SDK calls should live (`callGemini`), with self-verification
- `guard/` – enforcement: anchors, policy engine, scanners, citations, redaction, provenance, signer, telemetry, rate limits
- `fetch/` – Aegis fetch proxy handlers (mount in your existing Express/Next server)
- `index.ts` – orchestrator (`geminiAskGuarded`)

## How to wire in your app
- **Express route:**
  ```ts
  import { askExpressHandler } from "./src/gemini/routes/ask.express"; // create this thin wrapper in your app
  ```
  Or call the orchestrator directly:
  ```ts
  import { geminiAskGuarded } from "./src/gemini";
  const { status, body } = await geminiAskGuarded({ prompt: "..." });
  ```

## Replace stubs
- Implement the real Gemini SDK call inside `client/geminiClient.ts` (keep the chokepoint).
- Use a **KMS/sidecar** to sign `issueChallenge()` and set `GEMINI_SIGNED_CHALLENGE` at call-time.
- Replace placeholder keys in `config/*.pem`.

## Guarantees
- **Serious-claim enforcement** (block/redact without whitelisted citations).
- **Protected identity** safeguards (Pearce Robinson) with **name-agnostic** conflation detection.
- **Anchor-gated** execution + **tamper-evident** provenance.
