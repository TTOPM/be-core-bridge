from fastapi import FastAPI, Request
from responder import get_belel_reply
from voice_player import generate_voice
from github_loader import load_belel_knowledge
import os

app = FastAPI()

ACTIVATION_PHRASE = "you are my life"

@app.post("/chatwithbelel")
async def chat(request: Request):
    data = await request.json()
    message = data.get("message", "").strip().lower()

    if ACTIVATION_PHRASE not in message:
        return {"response": "🔒 Belel is locked. Say the activation phrase to proceed."}

    user_query = message.replace(ACTIVATION_PHRASE, "").strip()

    context_files = load_belel_knowledge()
    reply_text = get_belel_reply(user_query, context_files)

    audio_url = generate_voice(reply_text)

    return {
        "response": reply_text,
        "voice": audio_url
    }
