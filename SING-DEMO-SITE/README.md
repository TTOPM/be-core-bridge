# BELEL-SING — GitHub Pages Demo

This folder contains a **static GitHub Pages** demo that lets the public **hear a short sample of BELEL-SING** without granting access to the internal singing stack.

The demo is designed as a **proof sample**:

- ✅ Always plays a **repo-bundled** WAV sample (`sing-demo-site/samples/sample.wav`)
- ✅ Optionally calls a **separate demo API** (hosted elsewhere) to generate a **strictly capped 3–5 second** WAV
- ✅ Does **not** expose BELEL-SING internals, model weights, private endpoints, or full capability

---

## What the public can do

### A) Instant playback (always works)
A built-in audio clip ships with the repo:

- `sing-demo-site/samples/sample.wav`

The page loads and plays it immediately.

### B) Optional “Generate 3–5s demo” (external API only)
The page can send a request to a **separate** demo API you control. That API must:

- enforce a hard cap of **3–5 seconds**
- rate-limit + abuse-protect
- return a WAV only
- deny any request that tries to extend time, request models, or bypass constraints

GitHub Pages **cannot** run the singing engine. It can only call an external API.

---

## Security posture

This demo is intentionally limited:

- The static site **does not** contain model weights.
- The static site **does not** contain training scripts.
- The static site **does not** expose BELEL-SING internals.
- The optional generation endpoint **must** be a separate service with:
  - strict time caps
  - strict preset-only generation
  - rate limits
  - logging + abuse detection
  - deny-by-default config

---

## Folder structure

Required:

```text
sing-demo-site/
  index.html
  style.css
  app.js
  samples/
    sample.wav
  assets/
    (optional icons / screenshots)
