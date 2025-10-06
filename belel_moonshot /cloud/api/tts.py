import os, base64, requests
from .settings import VOICE_GATEWAY_URL, VOICE_ENGINE, VOICE_NAME
def to_prosody(tone,pacing,energy):
    return {"rate":round(0.7+pacing*0.6,2),"pitch":round(0.8+tone*0.4,2),"volume":round(0.7+energy*0.6,2)}
def synthesize(text:str, tone:float, pacing:float, energy:float, voice_name=None, engine=None)->bytes:
    payload={"engine":engine or VOICE_ENGINE,"voice":voice_name or VOICE_NAME,"text":text,
             "prosody":to_prosody(tone,pacing,energy),"require_disclosure":True,
             "jurisdiction":os.getenv("VOICE_JURISDICTION","EU")}
    url=f"{VOICE_GATEWAY_URL}/v1/tts/synthesize"
    r=requests.post(url,json=payload,timeout=60); r.raise_for_status()
    ct=r.headers.get("Content-Type","")
    if "application/json" in ct:
        data=r.json(); b64=data.get("audio_base64"); 
        if not b64: raise RuntimeError("TTS JSON missing audio_base64"); 
        return base64.b64decode(b64)
    return r.content
