import os
import requests
import uuid

VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def generate_voice(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    try:
        r = requests.post(url, headers=headers, json=payload)
        audio_filename = f"audio_{uuid.uuid4().hex}.mp3"
        with open(f"static/audio/{audio_filename}", "wb") as f:
            f.write(r.content)
        return f"/static/audio/{audio_filename}"
    except Exception:
        return None
