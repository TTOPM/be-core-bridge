
import os
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .emotion import classify_emotion
from .tts import synthesize
from . import memory

STATIC_DIR = os.environ.get("STATIC_DIR", "static")
AUDIO_DIR = os.environ.get("STATIC_AUDIO_DIR", os.path.join(STATIC_DIR, "audio"))
PRESETS_PATH = os.environ.get("BELEL_PRESETS_PATH", "config_presets.json")

with open(PRESETS_PATH, "r") as f:
    PRESETS = json.load(f)

app = FastAPI(title="chatwithbelel_pro", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ChatBody(BaseModel):
    message: str
    preset: Optional[str] = None
    emotion_hint: Optional[str] = None
    tone: Optional[float] = None
    pacing: Optional[float] = None
    energy: Optional[float] = None

def _select_preset(detected: str, requested: Optional[str]) -> Dict[str, float]:
    if requested and requested in PRESETS["presets"]:
        return PRESETS["presets"][requested]
    mapped = PRESETS["emotion_map"].get(detected, "neutral")
    return PRESETS["presets"].get(mapped, PRESETS["presets"]["neutral"])

def _blend_controls(base: Dict[str, float], overrides: Dict[str, Optional[float]]) -> Dict[str, float]:
    out = dict(base)
    for k in ("tone", "pacing", "energy"):
        v = overrides.get(k)
        if v is not None:
            out[k] = max(0.0, min(1.0, float(v)))
    return out

def generate_reply(history, user_text: str, emotion_label: str) -> str:
    """
    Placeholder text generation for offline packaging.
    You can wire this to your Belel LLM or any responder.
    """
    # Simple reflective strategy with memory awareness
    context = " ".join([f"{r}:{c}" for r, c, _ in history[-4:]])
    if emotion_label in ("sad","nervous","anxious"):
        style = "empathetic"
    elif emotion_label in ("angry","frustrated"):
        style = "calm and steady"
    elif emotion_label in ("happy","excited"):
        style = "warm and upbeat"
    else:
        style = "clear and helpful"
    return (f"I hear you. In a {style} tone: {user_text} "
            f"(I’m tracking your recent context to support continuity.)")

@app.get("/api/presets")
def get_presets():
    return PRESETS

@app.post("/api/chat")
def chat(body: ChatBody, x_session_id: Optional[str] = Header(default="session-default")):
    # Safety: activation phrase support (optional – disabled by default)
    # if "you are my life" not in body.message.lower():
    #     return {"error": "Activation phrase missing."}

    # Memory and emotion
    memory.append_message(x_session_id, "user", body.message)
    detected_label, intensity = classify_emotion(body.message)
    if body.emotion_hint:
        detected_label = body.emotion_hint

    base = _select_preset(detected_label, body.preset)
    controls = _blend_controls(base, {"tone": body.tone, "pacing": body.pacing, "energy": body.energy})

    # Generate text (replace with your responder if available)
    history = memory.get_history(x_session_id, limit=12)
    reply = generate_reply(history, body.message, detected_label)
    memory.append_message(x_session_id, "assistant", reply)

    # Synthesize to WAV via Belel Voice Gateway
    audio_path = synthesize(reply, controls["tone"], controls["pacing"], controls["energy"],
                            voice_name=os.environ.get("VOICE_NAME"), engine=os.environ.get("VOICE_ENGINE"))
    audio_url = f"/static/audio/{os.path.basename(audio_path)}"

    return {
        "response": reply,
        "voice": audio_url,
        "detected_emotion": detected_label,
        "intensity": intensity,
        "used_controls": controls
    }

@app.get("/healthz")
def healthz():
    return {"ok": True}
