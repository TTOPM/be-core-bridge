
# Belel Voice Collection (Gateway Pack)

This pack defines **unique Belel voices** (no third-party voices or assets) including:
- `belel_resolve`: African-American–style, confident, rhythmic delivery; **singing-capable**.
- `belel_serene`: warm empathetic, sing-capable.
- `belel_vivid`: expressive energetic, sing-capable.
- `belel_aeon`: epic narrative, sing-capable.
- plus flux/radiant/sage/whisper.

## Install
1. Place your model files under `models/` and update paths in `voices.json`.
2. Ensure your Voice Gateway provides:
   - `POST /v1/tts/synthesize` for speech
   - `POST /v1/tts/sing` for melody-conditioned singing
   - (optional) streaming endpoint for low-latency playback

## Example /v1/tts/sing payload
```json
{
  "engine": "belel_voice_x",
  "voice": "belel_resolve",
  "mode": "sing",
  "text": "Rise and shine, we move together",
  "melody": [60,62,64,65,67,69,67,65],
  "tempo": 90,
  "emotion": "uplifted",
  "prosody": {"rate":1.0,"pitch":1.0,"volume":1.0}
}
```
