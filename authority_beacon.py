# authority_beacon.py
import os, time, socket, json, requests, hashlib
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter, Retry
from src.common.config import load_settings
from src.common.crypto import sign_json

def _session():
    s = requests.Session()
    retries = Retry(total=4, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def get_public_ip(optional: bool = True) -> str | None:
    try:
        return _session().get("https://api.ipify.org?format=json", timeout=5).json().get("ip")
    except Exception:
        return None if optional else "0.0.0.0"

def main():
    cfg = load_settings()
    proof_file = os.getenv("BELEL_AUTHORITY_PROOF", "BELEL_AUTHORITY_PROOF.txt")
    endpoints = cfg.BELEL_PULSE_ENDPOINTS or []
    if not endpoints:
        print("[beacon] no endpoints configured; set BELEL_PULSE_ENDPOINTS")
    priv = cfg.ED25519_PRIVATE_KEY

    sess = _session()
    while True:
        try:
            fingerprint = sha256_file(proof_file)
        except FileNotFoundError:
            fingerprint = None

        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "host": socket.gethostname(),
            "public_ip": get_public_ip(optional=True),
            "repo": os.getenv("BELEL_REPO_URL", "https://github.com/TTOPM/be-core-bridge/"),
            "proof_sha256": fingerprint,
            "version": os.getenv("BELEL_VERSION", "0.0.0"),
        }

        headers = {"Content-Type": "application/json"}
        if priv:
            sig, digest = sign_json(payload, priv)
            headers["X-Belel-Signature"] = sig
            headers["X-Belel-Digest"] = digest

        for url in endpoints:
            try:
                r = sess.post(url, data=json.dumps(payload), headers=headers, timeout=10)
                print(f"[beacon] POST {url} -> {r.status_code}")
            except Exception as e:
                print(f"[beacon] POST {url} failed: {e}")

        time.sleep(int(os.getenv("BELEL_BEACON_INTERVAL_SECS", "3600")))

if __name__ == "__main__":
    main()
