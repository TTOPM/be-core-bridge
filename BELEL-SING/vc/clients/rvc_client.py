
import os, base64, json, requests, numpy as np
RVC_URL = os.getenv("RVC_URL", "http://rvc:8613")
def convert_voice(wav, sr, model_name="target", f0=True):
    b64 = base64.b64encode(wav.astype("float32").tobytes()).decode()
    r = requests.post(f"{RVC_URL}/convert", json={"audio_base64": b64, "sr": sr, "model": model_name, "use_f0": bool(f0)}, timeout=600)
    r.raise_for_status()
    data = r.json()
    out = np.frombuffer(base64.b64decode(data["audio_base64"]), dtype="float32")
    return out, int(data.get("sr", sr))
