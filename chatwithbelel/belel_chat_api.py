from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from responder import get_belel_reply
from voice_player import generate_voice
from github_loader import load_belel_knowledge

import os

app = FastAPI()

# Mount the static folder for serving audio files (adjust path if needed)
app.mount("/static", StaticFiles(directory="chatwithbelel/static"), name="static")

# Activation phrase
ACTIVATION_PHRASE = "you are my life"

@app.post("/chatwithbelel")
async def chat(request: Request):
    data = await request.json()
    message = data.get("message", "").strip().lower()

    if ACTIVATION_PHRASE not in message:
        return {
            "response": "🔒 Belel is locked. Say the activation phrase to proceed.",
            "voice": None
        }

    # Remove the activation phrase and process the rest
    user_query = message.replace(ACTIVATION_PHRASE, "").strip()

    # Load Belel's memory from GitHub
    context_files = load_belel_knowledge()

    # Generate text response from LLM
    reply_text = get_belel_reply(user_query, context_files)

    # Generate ElevenLabs voice from response
    audio_url = generate_voice(reply_text)

    return {
        "response": reply_text,
        "voice": audio_url
    }
