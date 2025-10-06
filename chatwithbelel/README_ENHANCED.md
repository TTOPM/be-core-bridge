
# chatwithbelel_pro — Belel-native, Emotionally Aware Voice Chat

This package upgrades **chatwithbelel** with:
- ✅ Emotion classifier + parametric TTS engine (tone/pacing/energy)
- ✅ Conversation memory (SQLite)
- ✅ JSON presets for voices & affect
- ✅ Polished Web UI with sliders for tone, pacing, energy
- ✅ One-command run (FastAPI + static assets)

> Built to work with **Belel Voice Gateway** (BELEL-VOICE). STT: `ws://<host>:8000/v1/asr/stream`, TTS: `POST http://<host>:8000/v1/tts/synthesize`.

---

## Quickstart

### 0) Requirements
- Python 3.9+
- Belel Voice Gateway running locally or reachable at `VOICE_GATEWAY_URL`
- (Optional) A reverse proxy/TLS if exposing to the internet

### 1) Install
```bash
cd chatwithbelel_pro/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure (optional)
Edit `../config_presets.json` to change default voice, presets, and emotion mapping.

Or set environment variables:
```bash
export VOICE_GATEWAY_URL="http://localhost:8000"
export VOICE_ENGINE="piper"
export VOICE_NAME="en_GB-sean-medium.onnx"
export STATIC_DIR="../static"
export STATIC_AUDIO_DIR="../static/audio"
export BELEL_PRESETS_PATH="../config_presets.json"
export BELEL_MEMORY_DB="../chat_memory.sqlite"
```

### 3) Run (one command)
```bash
uvicorn backend.main:app --reload --port 5173
```

Now open: **http://localhost:5173/static/index.html**

- Click **🎙️ Start Mic** to stream audio to Belel STT (if running).
- Type messages and use sliders to control **Tone / Pacing / Energy**.
- Select a **Preset** to snap to a style (you can still nudge sliders).

---

## How it works

### Emotion Classifier
A portable, rule-based detector (`backend/emotion.py`) returns `(label, intensity)` using small lexicons and simple modifier logic. Swap this for your model when ready and keep the same function signature.

### TTS Parameter Engine
`backend/tts.py` maps sliders (0..1) → engine-agnostic `rate/pitch/volume`. The request payload:
```json
{
  "engine": "piper",
  "voice": "en_GB-sean-medium.onnx",
  "text": "Hello there",
  "prosody": {"rate": 1.0, "pitch": 1.0, "volume": 1.0},
  "require_disclosure": true,
  "jurisdiction": "EU"
}
```
Adjust in your Belel gateway as needed.

### Memory
`backend/memory.py` keeps rolling history per `X-Session-Id` header so the assistant can stay consistent over time.

### API
- `GET /api/presets` → the JSON presets
- `POST /api/chat` body:
  ```json
  { "message": "...", "preset": "warm_empathic", "tone": 0.7, "pacing": 0.45, "energy": 0.55 }
  ```
  returns:
  ```json
  {
    "response": "... text ...",
    "voice": "/static/audio/audio_ab12cd34.wav",
    "detected_emotion": "nervous",
    "intensity": 0.72,
    "used_controls": {"tone":0.70,"pacing":0.45,"energy":0.55}
  }
  ```

### Frontend
- `/static/index.html` + `/static/app.js` + `/static/styles.css`
- Sliders feed the parametric engine; the player auto-plays the returned WAV.

---

## Extending to “next-level”

- Replace `generate_reply(...)` in `backend/main.py` with your Belel LLM/tool-use pipeline.
- Upgrade `emotion.py` to a proper classifier (e.g., fine-tuned model) keeping the same return shape.
- Implement live **TTS streaming** over WS in your gateway; the UI is ready to adapt.

---

## Security & Compliance
- The sample request sets `require_disclosure: true` and `jurisdiction: "EU"`. Wire these to your gateway policy checks.
- If hosting cross-origin, configure CORS in `backend/main.py`.

---

## License
This package is provided as-is for integration with your Belel stack.
