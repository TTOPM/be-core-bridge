
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional
from starlette.responses import StreamingResponse
import os, base64, tempfile, io, wave, numpy as np

# ACL
ALLOWED_EMAIL_DOMAINS = os.getenv('ALLOWED_EMAIL_DOMAINS','pearcerobinson.com,ttopm.com,scarlet41.org,prfdn.org,belel.ai').split(',')
DEV_ALLOW_ALL = os.getenv('DEV_ALLOW_ALL','false').lower()=='true'

def _check_access(request: Request):
    if DEV_ALLOW_ALL: return
    email = request.headers.get("X-Auth-Email","")
    if '@' not in email: from fastapi import HTTPException; raise HTTPException(403, "Missing X-Auth-Email")
    domain = email.split('@')[-1].lower().strip()
    if domain not in [d.strip().lower() for d in ALLOWED_EMAIL_DOMAINS]:
        from fastapi import HTTPException; raise HTTPException(403, "Email domain not permitted")

# Pipeline glue (expects sidecars or local)
from inference.pipeline import sing

app = FastAPI(title="BELEL-SING (Checkpoint Ready)")

class SingBody(BaseModel):
    lyrics: str
    midi_base64: Optional[str] = None
    midi_url: Optional[str] = None
    controls: Optional[dict] = None

@app.post("/v1/sing")
async def sing_api(body: SingBody, request: Request):
    _check_access(request)
    if not body.midi_base64 and not (body.controls or {}).get("musicxml_base64"):
        return {"error":"Provide midi_base64 or controls.musicxml_base64"}
    midi_path = None; xml_path = None
    if body.midi_base64:
        mb = base64.b64decode(body.midi_base64)
        f = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
        f.write(mb); f.flush(); midi_path=f.name
    if (body.controls or {}).get("musicxml_base64"):
        xb = base64.b64decode(body.controls["musicxml_base64"])
        x = tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False)
        x.write(xb); x.flush(); xml_path=x.name
    wav, sr = sing(body.lyrics, midi_path=midi_path, musicxml_path=xml_path, controls=body.controls or {})
    import soundfile as sf, io
    buf = io.BytesIO(); sf.write(buf, wav, sr, format="WAV")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return {"audio_base64": b64, "sr": sr}

@app.post("/v1/sing/stream")
async def sing_stream(body: SingBody, request: Request):
    _check_access(request)
    if not body.midi_base64 and not (body.controls or {}).get("musicxml_base64"):
        return {"error":"Provide midi_base64 or controls.musicxml_base64"}
    midi_path = None; xml_path = None
    if body.midi_base64:
        mb = base64.b64decode(body.midi_base64)
        f = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
        f.write(mb); f.flush(); midi_path=f.name
    if (body.controls or {}).get("musicxml_base64"):
        xb = base64.b64decode(body.controls["musicxml_base64"])
        x = tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False)
        x.write(xb); x.flush(); xml_path=x.name
    wav, sr = sing(body.lyrics, midi_path=midi_path, musicxml_path=xml_path, controls=body.controls or {})

    def gen():
        chunk = int(sr*0.5)
        for i in range(0, len(wav), chunk):
            seg = wav[i:i+chunk]
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
                pcm = (np.clip(seg, -1, 1)*32767).astype("int16").tobytes()
                w.writeframes(pcm)
            yield buf.getvalue()

    return StreamingResponse(gen(), media_type="audio/wav")
