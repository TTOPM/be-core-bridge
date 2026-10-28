# Moshi / PersonaPlex bring-up — entirely optional

These instructions help establish a **separate** model service. They do not install anything on Belel and do not modify its production code.

## Model A: Kyutai Moshi, preferred first research engine

Official repo: https://github.com/kyutai-labs/moshi

1. Provision a compatible local GPU, Apple MLX machine or self-hosted server. Follow the upstream requirements and licence obligations.
2. Clone **the upstream model's repository into a different working directory**, not over the Belel repo.
3. Use Kyutai's documented inference start command for its Python backend:

```bash
python -m moshi.server --hf-repo kyutai/moshika-pytorch-bf16
```

4. Verify the official Moshi Web UI works directly with microphone and speech before testing BAIN. The default server listens on port 8998 and typically exposes the binary WebSocket at `/api/chat`.
5. Start BAIN's protocol translator only after the upstream model is running:

```bash
cd services/belel-acoustic-runtime
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BELEL_DUPLEX_UPSTREAM=ws://127.0.0.1:8998/api/chat
export BELEL_DUPLEX_ALLOWED_ORIGIN=http://localhost:8080
export BELEL_DUPLEX_TOKEN='CHOOSE_AN_EPHEMERAL_SECRET'
python duplex_proxy.py
```

The translator is loopback-only and has **no microphone**. The web client must explicitly authorise and supply audio, using the standardized `BelelSelfHostedDuplexGateway` adapter. Model audio is returned for evaluation, not automatically played or granted Belel tool authority.

## Model B: NVIDIA PersonaPlex, voice/role-conditioned comparison

Official repo: https://github.com/NVIDIA/personaplex

1. Accept the NVIDIA Open Model License and gated model access on Hugging Face.
2. Follow the official installation instructions and start the model's own live inference server; the project documents `SSL_DIR=$(mktemp -d); python -m moshi.server --ssl "$SSL_DIR"` for TLS.
3. PersonaPlex versions may require explicit `voice_prompt`, `text_prompt`, and API authentication in the WebSocket URL. Configure these only in the **server-side** `BELEL_DUPLEX_UPSTREAM`, never in browser source.
4. Verify server/client TLS and codec compatibility in an isolated test. Do not disable TLS verification or publish the local service to the internet.
5. Preserve Belel's signature voice: PersonaPlex generated voice remains in shadow mode until explicit review and approval.

## Important: protocol limitation

The local translator implements the Kyutai Moshi-family typed Opus frame convention. Server revisions or alternate PersonaPlex builds may differ. A production-ready transport requires end-to-end audio tests against the installed model version; this package has **not** run that GPU-backed validation. If packets are not understood, keep BAIN disabled and use the upstream official client.

## Dessa compatibility

`block-dessa-future` is recorded as a model-family profile only. No unavailable download, API or inference route is used. Future APIs can be implemented through the same `DuplexModelAdapter` interface once terms, availability and hardware are verified.

## Why this can surpass a single speech-to-speech model

Moshi/PersonaPlex supply a low-latency acoustic conversational layer. Belel still supplies grounded reasoning, tools, long-term permissioned memory, context, camera/vision integration, working orb presence and trusted actions. The full system can be broader than a stand-alone speech model, but superiority must be proven with reproducible benchmarks rather than assertions.
