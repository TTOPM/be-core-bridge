
import os
import uuid
import json
from typing import Dict, Any
import requests

VOICE_URL = os.environ.get("VOICE_GATEWAY_URL", "http://localhost:8000")
VOICE_ENGINE = os.environ.get("VOICE_ENGINE", "piper")
VOICE_NAME = os.environ.get("VOICE_NAME", "en_GB-sean-medium.onnx")
STATIC_AUDIO_DIR = os.environ.get("STATIC_AUDIO_DIR", "static/audio")

def _blend(a: float, b: float, w: float) -> float:
    return a * (1.0 - w) + b * w

def to_engine_params(tone: float, pacing: float, energy: float) -> Dict[str, Any]:
    """
    Map tone/pacing/energy in [0,1] to engine-specific prosody controls.
    Kept generic: rate, pitch, volume. Engines can adapt.
    """
    # rate: 0.7..1.3 (slower..faster)
    rate = 0.7 + pacing * 0.6
    # pitch: 0.8..1.2 (lower..higher)
    pitch = 0.8 + tone * 0.4
    # volume/energy: 0.7..1.3
    volume = 0.7 + energy * 0.6
    return {"rate": round(rate, 2), "pitch": round(pitch, 2), "volume": round(volume, 2)}

def synthesize(text: str, tone: float, pacing: float, energy: float, voice_name: str = None, engine: str = None) -> str:
    engine = engine or VOICE_ENGINE
    voice_name = voice_name or VOICE_NAME
    params = to_engine_params(tone, pacing, energy)
    payload = {
        "engine": engine,
        "voice": voice_name,
        "text": text,
        "prosody": params,
        "require_disclosure": True,
        "jurisdiction": os.environ.get("VOICE_JURISDICTION", "EU")
    }
    url = f"{VOICE_URL}/v1/tts/synthesize"
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    # Assume raw WAV/bytes returned or JSON with {audio: <bytes>}. We try bytes first.
    out_id = str(uuid.uuid4())[:8]
    out_path = os.path.join(STATIC_AUDIO_DIR, f"audio_{out_id}.wav")
    os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)
    # Try to detect JSON vs bytes
    content_type = r.headers.get("Content-Type", "")
    if "application/json" in content_type:
        data = r.json()
        # support base64 audio as fallback
        import base64
        audio_b64 = data.get("audio_base64")
        if not audio_b64:
            raise RuntimeError("TTS response missing audio data")
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(audio_b64))
    else:
        with open(out_path, "wb") as f:
            f.write(r.content)
    return out_path
