import json, base64
from typing import Optional
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from .observability import TimingMiddleware, metrics_router
from pydantic import BaseModel
from .settings import PRESETS_PATH
from . import memory, policy, tts, emotions, reasoner, tools
from .planner import Planner
from .policy_pipeline import PolicyGraph, Disclosure, Harm, Bias, Jurisdiction, Provenance, AuditLog, PolicyContext
PRESETS=json.load(open(PRESETS_PATH))
app=FastAPI(title="Belel Moonshot API", version="0.1")

    # Initialize planner with tool registry
    _PLANNER = Planner({
        "echo": lambda a: tools.run_tool("echo", a),
        "web.search": lambda a: tools.run_tool("web.search", a),
        "calendar.search": lambda a: tools.run_tool("calendar.search", a),
        "code.generate": lambda a: tools.run_tool("code.generate", a),
    })
    
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
class ChatBody(BaseModel):
    message:str
    preset: Optional[str]=None
    persona: Optional[str]="Belel"
    emotion_hint: Optional[str]=None
    tone: Optional[float]=None
    pacing: Optional[float]=None
    energy: Optional[float]=None
def _preset_for(label, requested):
    if requested and requested in PRESETS["presets"]: return PRESETS["presets"][requested]
    mapped=PRESETS["emotion_map"].get(label,"neutral"); return PRESETS["presets"].get(mapped, PRESETS["presets"]["neutral"])
@app.get("/healthz")
def healthz(): return {"ok":True}
@app.get("/api/presets")
def get_presets(): return PRESETS
@app.post("/api/chat")
def chat(body:ChatBody, x_session_id:str=Header(default="session-default"), x_disclosed:str=Header(default="false")):
    memory.append(x_session_id, "user", body.message)
    label,_=emotions.classify(body.message)
    if body.emotion_hint: label=body.emotion_hint
    base=_preset_for(label, body.preset)
    tone=float(body.tone) if body.tone is not None else base["tone"]
    pacing=float(body.pacing) if body.pacing is not None else base["pacing"]
    energy=float(body.energy) if body.energy is not None else base["energy"]
    hist=memory.history(x_session_id, 24)
    raw=reasoner.generate_reply(hist, body.message, body.persona, emotion_hint=label)
        # Planner auto-activation heuristic (can make this explicit via payload)
        if any(k in body.message.lower() for k in ['plan','schedule','search','find','code']):
            steps = _PLANNER.plan(body.message)
            res = _PLANNER.execute(steps, retries=1)
            raw = raw + "\n\n" + (res.output if res.output else "")
    graph = PolicyGraph([Disclosure(), Harm(), Bias(), Jurisdiction(), Provenance(), AuditLog()])
        ctx = PolicyContext(user_text=body.message, model_text=raw, session_disclosed=(x_disclosed.lower()=="true"))
        ctx = graph.run(ctx)
        guarded = ctx.model_text
        blocked = bool((ctx.meta or {}).get('blocked'))
        disclosed_now = bool((ctx.meta or {}).get('disclosed_now'))
    if blocked:
        memory.append(x_session_id, "assistant", guarded)
        return {"response":guarded, "blocked":True}
    audio=tts.synthesize(guarded, tone, pacing, energy)
    voice_b64=base64.b64encode(audio).decode("utf-8")
    memory.append(x_session_id, "assistant", guarded)
    return {"response":guarded,"voice_base64":voice_b64, "voice_stream_url": null,"mimetype":"audio/wav",
            "detected_emotion":label,"controls":{"tone":tone,"pacing":pacing,"energy":energy},
            "disclosed_now":disclosed_now}
