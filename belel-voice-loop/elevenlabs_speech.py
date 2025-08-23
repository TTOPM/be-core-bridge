# Text-to-Speech via ElevenLabs
from elevenlabs import generate, play, set_api_key
import os

set_api_key(os.getenv("ELEVENLABS_API_KEY"))

def speak(text: str):
    try:
        audio = generate(text=text, voice="Belel", model="eleven_monolingual_v1")
        play(audio)
    except Exception as e:
        print("Fallback: Text spoken output failed.", e)
