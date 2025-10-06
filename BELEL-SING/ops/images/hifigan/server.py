
from fastapi import FastAPI
from pydantic import BaseModel
import base64, numpy as np, os, sys, importlib.util

PLUGIN_PATH = "/_plugins/hifigan_infer.py"
def _load_plugin():
    if os.path.exists(PLUGIN_PATH):
        spec = importlib.util.spec_from_file_location("hg_plugin", PLUGIN_PATH)
        mod = importlib.util.module_from_spec(spec); sys.modules["hg_plugin"] = mod; spec.loader.exec_module(mod)
        return mod
    return None
_plugin = _load_plugin()

app = FastAPI(title="HiFi-GAN Vocoder Sidecar (Plugin-Aware)")

class MelBody(BaseModel):
    mel_base64: str

@app.post("/mel2wav")
def mel2wav(body: MelBody):
    mel = np.frombuffer(base64.b64decode(body.mel_base64), dtype=np.float32)
    mel = mel.reshape(80, -1)
    sr = 44100
    if _plugin and hasattr(_plugin, "mel2wav"):
        wav, sr = _plugin.mel2wav(mel)
    else:
        wav = np.zeros(sr, dtype=np.float32)
    b64 = base64.b64encode(wav.astype("float32").tobytes()).decode()
    return {"audio_base64": b64, "sr": sr}
