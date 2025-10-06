
import os, base64, json, requests, numpy as np
VOC_URL = os.getenv("VOCODER_URL", "http://hifigan:8612")
def mel2wav(mel):
    mel_bytes = mel.astype("float32").tobytes()
    b64 = base64.b64encode(mel_bytes).decode()
    r = requests.post(f"{VOC_URL}/mel2wav", json={"mel_base64": b64}, timeout=600)
    r.raise_for_status()
    data = r.json()
    wav = np.frombuffer(base64.b64decode(data["audio_base64"]), dtype="float32")
    sr = int(data.get("sr", 44100))
    return wav, sr
