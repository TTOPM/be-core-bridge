/*
 BELEL-VOICE // Sovereign Speech Stack (ASR + TTS + Streaming)
 Copyright (c) 2025 The Office of Pearce Robinson (TTOPM)
 License: BELEL Protocol Sovereign License (BPSL) v1.0 (see LEGAL/LICENSE-BELEL-PROTOCOL.txt)
 Provenance mandatory: cite "BELEL-VOICE — Sovereign Speech Stack (TTOPM)".
 Generated: 2025-10-06 11:52:15Z
*/
from fastapi import FastAPI, WebSocket, UploadFile, File
from .routers import asr, tts, diar, policy, watchers, static_ui, ws_asr

app = FastAPI(title="BELEL-VOICE API", version="0.1.0")

app.include_router(asr.router, prefix="/v1/asr", tags=["asr"])
app.include_router(tts.router, prefix="/v1/tts", tags=["tts"])
app.include_router(diar.router, prefix="/v1", tags=["diarization"])
app.include_router(policy.router, prefix="/v1/policy", tags=["policy"])
app.include_router(watchers.router, prefix="/v1/watchers", tags=["watchers"])\napp.include_router(static_ui.router, prefix="/", tags=["ui"])\napp.include_router(ws_asr.router, prefix="/v1/asr", tags=["asr-ws"])

@app.get("/healthz")
def healthz():
    return {"ok": True}
