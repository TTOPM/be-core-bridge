
import base64
from fastapi.testclient import TestClient
from cloud.api.main import app

client = TestClient(app)

def test_health():
    r = client.get("/healthz"); assert r.status_code==200

def test_presets():
    r = client.get("/api/presets"); assert r.status_code==200; assert "presets" in r.json()

def test_chat_minimal(monkeypatch):
    # Monkeypatch TTS to avoid external call
    import cloud.api.tts as tts
    def fake_syn(text, t,p,e, voice_name=None, engine=None): return b"RIFF....WAVE"
    monkeypatch.setattr(tts, "synthesize", fake_syn)
    r = client.post("/api/chat", json={"message":"hello there"})
    assert r.status_code==200
    j=r.json()
    assert "response" in j and "voice_base64" in j
    base64.b64decode(j["voice_base64"])
