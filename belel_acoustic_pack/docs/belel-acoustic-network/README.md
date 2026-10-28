# BELEL | Sovereign Acoustic Intelligence Network (BAIN)

**Engineering priority 01 — isolated additive module, v1.0.0 — 28 October 2026**

## Important: what uploading does

**Uploading these files does not modify or run any of Belel's existing modules.** No current Belel source file is replaced. Nothing is imported into App.tsx or main.tsx. The existing orb, speech systems, model routing, network fabric, authentication, voice profile, calling and audio mixers keep behaving as before.

This package supplies a functioning *coordination, observability, policy, pronunciation and wake-assessment foundation*; **it does not claim that a new trained wake model or GPU speech model is included**. A separately licensed custom wake model and independently deployed Moshi or PersonaPlex server are needed for model inference.

The package has no npm installation step and changes no root `package.json` or lockfile. All dependencies for its **optional local Python services** are isolated in `services/belel-acoustic-runtime/requirements.txt`.

## File tree (all paths are NEW)

- `src/lib/belel-acoustic-network/`: contracts, zero-trust config, event fabric, precision pronunciation, wake verification, duplex turn-state controller, model registry, telemetry, passive legacy-event observer, opt-in local inference adapters, benchmark evaluator.
- `services/belel-acoustic-runtime/wake_server.py`: optional loopback-only openWakeWord gateway using an owner-supplied licensed custom model.
- `services/belel-acoustic-runtime/duplex_proxy.py`: optional loopback-only Moshi-family Opus/WebSocket protocol translator.
- `tests/belel-acoustic-network/`: isolated non-destructive tests and integration safeguards.
- `docs/belel-acoustic-network/`: deployment policy, architecture, benchmarks, licensing and operating instructions.
- `tools/belel-acoustic-network/verify_new_only.py`: asserts the package never overwrites a destination file.

## What the architecture does that a single speech model cannot

BAIN separates (1) capture governance, (2) a trained wake model, (3) independent verification, (4) perception, (5) pronunciation intelligence, (6) user/assistant overlap handling, (7) real-time speech-to-speech candidates, and (8) authoritative Belel reasoning/actions and voice identity.

**Dessa-class performance is an aspiration, not a reported result.** It is not possible to prove Belel exceeds Siri, Alexa, Moshi, PersonaPlex or Dessa without comparable validated benchmarks, hardware and live tests. The design *can* potentially exceed a single speech model in capabilities by joining its full-duplex acoustic timing with Belel's existing vision, memory, multi-agent coordination, document tools and completed orb interface.

## Models and risk

- **Kyutai Moshi** — released full-duplex streaming speech framework; code has MIT/Apache components, weights CC-BY 4.0. Preferred **first experimental engine**.
- **NVIDIA PersonaPlex** — Moshi-derived full-duplex streaming with explicit voice conditioning and role prompt; MIT code; gated weights under NVIDIA Open Model License. Preferred **second comparative engine**.
- **Block Dessa** — research preview with no verified public installable checkpoint/API as of 28 October 2026; only a future interface target. No remote Dessa dependency.
- **Fish Speech S2 Pro** — already in Belel, and excellent for expressive TTS; **not a substitute for a full-duplex conversation engine**. S2-Pro weights are under Fish Audio Research License; review commercial deployment rights. Preserve Belel's current installation and preferences.
- **openWakeWord** — code Apache 2.0, bundled pretrained weights commonly CC BY-NC-SA. Do not commercialise restricted weights. Owner-supplied trained `Hey Belel` weights require their own provenance and licence review.

## Architecture and phase gates

**Phase 0, uploaded:** modules are dormant and safe; all existing features remain unchanged.

**Phase 1, explicit observability:** in an owner-approved development-only entrypoint (not supplied or installed by this package), create a `BelelAcousticNetwork()` and attach it to `window` to observe known legacy speech events. This feeds BAIN's in-memory bus without any reverse command or mic ownership.

**Phase 2, shadow wake:** train a proper Belel keyword-spotting model and start the optional local inference service; hand it PCM that comes from an existing consented microphone capture pipeline. Train on diverse speakers, accents, noise, near-miss phrases and actual device acoustics. Never use the current RMS-peak heuristic as the label oracle. Independent verifier must confirm wake.

**Phase 3, shadow duplex:** launch Moshi or PersonaPlex using its official instructions and model licence. Optionally launch the local protocol translator. Receive model output for assessment ONLY. No model is allowed to authoritatively execute tools, write to permanent memory, override Belel's current TTS identity or control the orb.

**Phase 4, approved rollout:** after cross-device tests, explicit permission and a reviewed adapter change, enable audio sharing and optional output routing in a limited environment with a kill switch. Roll back instantly on any regression.

## Quick verification (without importing into Belel)

```bash
node --experimental-transform-types --test tests/belel-acoustic-network/*.test.ts
```

Node.js 22.16 or later is suggested for its built-in TS transformation. Python syntax can be checked independently:

```bash
python -m py_compile services/belel-acoustic-runtime/wake_server.py services/belel-acoustic-runtime/duplex_proxy.py
```

No existing tests or deployment commands were modified.

## How to upload into GitHub safely

Do **not** upload the `.zip` to GitHub web's `Upload files` control expecting it to expand automatically. Unzip locally, keeping directory structure, then push **only the listed new directories/files**. First execute:

```bash
python tools/belel-acoustic-network/verify_new_only.py --destination /path/to/your/Belel-repository --package /path/to/unzipped-package
```

The checker intentionally fails if any destination file already exists. A normal `git status` and code review must follow. Do not change tracked files as part of this import.

## Official model sources

- https://github.com/kyutai-labs/moshi
- https://github.com/NVIDIA/personaplex
- https://research.nvidia.com/labs/adlr/personaplex/
- https://github.com/dscripka/openWakeWord
- https://github.com/fishaudio/fish-speech
- https://block.xyz/dessa
