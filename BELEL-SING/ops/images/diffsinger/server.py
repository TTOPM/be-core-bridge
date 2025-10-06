
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import base64, numpy as np, importlib.util, os, sys

# Load plugin if present
PLUGIN_PATH = "/_plugins/diffsinger_infer.py"
def _load_plugin():
    if os.path.exists(PLUGIN_PATH):
        spec = importlib.util.spec_from_file_location("ds_plugin", PLUGIN_PATH)
        mod = importlib.util.module_from_spec(spec); sys.modules["ds_plugin"] = mod; spec.loader.exec_module(mod)
        return mod
    return None
_plugin = _load_plugin()

app = FastAPI(title="DiffSinger Inference Sidecar (Plugin-Aware)")

class InferBody(BaseModel):
    phones: List[int]
    f0: List[float]
    controls: Optional[dict] = None

@app.post("/infer")
def infer(body: InferBody):
    if _plugin and hasattr(_plugin, "infer"):
        mel = _plugin.infer(body.phones, body.f0, body.controls or {})
    else:
        # Fallback: return silence mel
        T = max(len(body.f0), 400); mel = np.zeros((80,T), dtype=np.float32)
    b64 = base64.b64encode(mel.astype("float32").tobytes()).decode()
    return {"mel_base64": b64, "n_mels": 80}
