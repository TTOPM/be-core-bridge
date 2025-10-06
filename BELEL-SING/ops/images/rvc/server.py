
from fastapi import FastAPI
from pydantic import BaseModel
import base64, numpy as np, os, sys, importlib.util

PLUGIN_PATH = "/_plugins/rvc_infer.py"
def _load_plugin():
    if os.path.exists(PLUGIN_PATH):
        spec = importlib.util.spec_from_file_location("rvc_plugin", PLUGIN_PATH)
        mod = importlib.util.module_from_spec(spec); sys.modules["rvc_plugin"] = mod; spec.loader.exec_module(mod)
        return mod
    return None
_plugin = _load_plugin()

app = FastAPI(title="RVC Sidecar (Plugin-Aware)")

class VCBody(BaseModel):
    audio_base64: str
    sr: int
    model: str = "target"
    use_f0: bool = True

@app.post("/convert")
def convert(body: VCBody):
    wav = np.frombuffer(base64.b64decode(body.audio_base64), dtype=np.float32)
    sr = body.sr
    if _plugin and hasattr(_plugin, "convert"):
        wav, sr = _plugin.convert(wav, sr, model=body.model, use_f0=body.use_f0)
    b64 = base64.b64encode(wav.astype("float32").tobytes()).decode()
    return {"audio_base64": b64, "sr": sr}
