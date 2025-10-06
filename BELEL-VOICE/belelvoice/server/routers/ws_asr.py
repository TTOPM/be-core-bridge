from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import tempfile, wave, time, os
from ..trust.audit import audit_hash

router = APIRouter()

@router.websocket("/stream")
async def ws_stream(ws: WebSocket):
    await ws.accept()
    # In production: feed chunks to streaming ASR (VAD + partials)
    pcm_path = tempfile.mktemp(suffix=".webm")
    try:
        while True:
            data = await ws.receive_bytes()
            # Here we would pass data to ASR stream and emit partials
            await ws.send_text('{"partial":"..."}')
    except WebSocketDisconnect:
        # On close: finalize ASR, synthesize a reply via local TTS
        # Placeholder: create a local URL to a static wav (or generated file)
        reply_url = "file://" + os.path.abspath(__file__)
        await ws.close()
