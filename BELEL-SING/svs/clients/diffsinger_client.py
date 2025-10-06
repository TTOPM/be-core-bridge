
import os, base64, json, requests, numpy as np
SVS_URL = os.getenv("SVS_URL", "http://diffsinger:8611")
def infer_mel(phones_ids, f0, controls=None):
    payload = {"phones": phones_ids, "f0": f0, "controls": controls or {}}
    r = requests.post(f"{SVS_URL}/infer", json=payload, timeout=600)
    r.raise_for_status()
    data = r.json()
    mel = np.frombuffer(base64.b64decode(data["mel_base64"]), dtype="float32")
    n_mels = data.get("n_mels", 80); T = mel.size // n_mels
    return mel.reshape(n_mels, T)
