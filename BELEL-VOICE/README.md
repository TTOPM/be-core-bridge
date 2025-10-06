> **Vision — Belel-Voice**  
> Our voices must be unique, defining, and alive. They should carry the same depth, realism, and expressive range as the most advanced systems on Earth — ElevenLabs, OpenAI, and every benchmark of generative speech to date. Each voice must project human authenticity: the breath, the pause, the subtle emotion that makes it feel lived-in. **Belel-Voice will meet and surpass** the expressive power, tonal precision, and performance quality of the world’s leading AI voice platforms, while remaining fully sovereign, self-evolving, and ethically governed. These are not synthetic voices; they are living signatures — crafted to be first-class in sound, in feeling, and in truth.


# BELEL-VOICE — Sovereign Speech Stack (ASR/STT + TTS)

![status](https://img.shields.io/badge/status-gold%20standard-brightgreen)
![license](https://img.shields.io/badge/license-BPSL%20v1.0-blue)
![privacy](https://img.shields.io/badge/privacy-on%20device%20%2F%20on%20prem-informational)
![compliance](https://img.shields.io/badge/compliance-EU%20AI%20Act%20labeling%2Fconsent-success)

**Date:** 2025-10-06 11:52:15Z

A complete, **OpenAI‑independent** speech stack for **on-device** and **on‑prem** deployments:
- **ASR**: faster‑whisper (Whisper‑v3 via CTranslate2), MMS, or NVIDIA Riva.
- **Diarization**: pyannote (switchable to NVIDIA NeMo/SpeechBrain).
- **TTS**: Piper (lightweight, offline), XTTS‑v2 (zero‑shot cloning with consent), or Riva TTS.
- **Streaming**: WebSocket low‑latency ASR + chunked TTS synthesis; VAD; ITN; profanity redaction (optional).
- **Compliance**: watermarking hooks, **EU AI Act** disclosure, consent registry, anti‑spoof, and audit ledger.

> Heavy models are not bundled; adapters are ready. Plug your chosen models in `belelvoice/adapters/*`.


## Offline / No-Paid-Services Mode
Use `Piper` (TTS) + `faster-whisper` (ASR). Place models under `models/` (see federation README).  
Run:
```bash
docker compose --profile voice up -d
```
This uses only local CPU/GPU resources. No calls to OpenAI or any paid API are required.

## Premium Expressive Layer
- **XTTS-v2** (zero-shot cloning, local) + **BigVGAN** vocoder hook for studio timbre.
- **ProsodyController** for SSML-like tags: `<speak style="warm" pitch="+2st" rate="0.95">`.

Enable by pointing to local models in `belelvoice/config.yaml` and switching `engine="xtts"` in requests.

## CLI Quick Test
```bash
./tools/belelvoice_say.py --text "This is Belel, speaking locally with a natural human voice." --voice en_GB --engine piper
```

## Egress-Denied Profile
Start fully offline (no outbound traffic) with an internal-only network:
```bash
cd ../BELEL-FEDERATION
docker compose -f docker-compose.egress-denied.yml --profile voice-egress-denied up -d
```
Then open the **local UI** (served by BELEL-VOICE):
```
http://localhost:8000/webui
```

> The iptables script blocks outbound traffic except private ranges; adjust CIDRs as needed.
