# Compatibility API exposing /chatwithbelel for legacy clients.
# Delegates to /api/chat from backend.main.

import os, json
from fastapi import FastAPI, Request, Header
from fastapi.staticfiles import StaticFiles
from backend.main import app as core_app, chat as core_chat, ChatBody

app = FastAPI(title="chatwithbelel_compat", version="1.0.0")
app.mount("/static", StaticFiles(directory=os.environ.get("STATIC_DIR","static")), name="static")

@app.post("/chatwithbelel")
async def chatwithbelel(req: Request, x_session_id: str = Header(default="session-default")):
    data = await req.json()
    message = data.get("message","")
    preset = data.get("preset")
    tone = data.get("tone")
    pacing = data.get("pacing")
    energy = data.get("energy")
    body = ChatBody(message=message, preset=preset, tone=tone, pacing=pacing, energy=energy)
    return core_chat(body, x_session_id=x_session_id)

@app.get("/healthz")
def healthz():
    return {"ok": True, "compat": True}
