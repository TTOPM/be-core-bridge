import requests, time, pathlib

def read_local(path: str):
    p = pathlib.Path(path)
    if p.exists() and p.is_file():
        return {"ok": True, "status": 200, "content": p.read_bytes(), "url": str(p), "tool": "local"}
    return {"ok": False, "status": 404, "error": "not found", "url": str(p), "tool": "local"}

def http_get(url: str, headers: dict | None = None, retries: int = 3, timeout=15):
    backoff = 1.5
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(url, headers=headers or {}, timeout=timeout)
            if r.status_code == 200:
                return {"ok": True, "status": 200, "content": r.content, "headers": dict(r.headers), "url": url, "tool": "http"}
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff**i); continue
            return {"ok": False, "status": r.status_code, "error": r.text, "url": url, "tool": "http"}
        except Exception as e:
            last_err = str(e); time.sleep(backoff**i)
    return {"ok": False, "status": 0, "error": last_err or "unknown", "url": url, "tool": "http"}
