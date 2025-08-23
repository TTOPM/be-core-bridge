import os
import requests
import uuid

VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def generate_voice(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.8,
            "style": 0.3,
            "use_speaker_boost": True
        }
    }
    filename = f"audio_{uuid.uuid4().hex}.mp3"
    path = f"chatwithbelel/static/audio/{filename}"

    r = requests.post(url, headers=headers, json=payload)
    with open(path, "wb") as f:
        f.write(r.content)
    return f"/static/audio/{filename}"
