from fastapi import FastAPI
from pydantic import BaseModel
import subprocess, tempfile, os, uuid

app = FastAPI()

class TTSIn(BaseModel):
    voice: str
    text: str
    language: str | None = None

@app.get("/health")
def health():
    return {"status": "ok", "service": "BELEL-VOICE"}

@app.post("/tts")
def tts(payload: TTSIn):
    # Example: call your synthesize.py with voices.json
    out = f"/tmp/{uuid.uuid4().hex}.wav"
    cmd = [
        "python", "synthesize.py",
        "--config", "voices.json",
        "--voice", payload.voice,
        "--text", payload.text,
        "--out", out
    ]
    if payload.language:
        cmd.extend(["--language", payload.language])

    subprocess.check_call(cmd)
    # Return path or serve bytes; here we just return a file path
    return {"audio_path": out}
