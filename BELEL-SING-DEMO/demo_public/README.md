# BELEL-SING — Public Demo (3–5s capped)

This is a deliberately constrained public demonstration UI + API.

## What it does
- Serves a small web page at `/`
- Generates a short WAV at `/v1/sing/demo.wav?lyrics=...&seconds=3|5`
- Enforces:
  - 3–5 second output only
  - max 80 characters of input
  - per-IP rate limits
  - process-level concurrency cap
- Runs in:
  - **fallback mode**: always emits a real WAV (synthetic melody)
  - **internal mode**: proxies to your private BELEL-SING `/v1/sing/stream` if configured

## Run locally
```bash
cd BELEL-SING/demo_public
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
Open: http://127.0.0.1:8000
docker build -t belel-sing-demo -f BELEL-SING/demo_public/Dockerfile .
docker run -p 8080:8080 belel-sing-demo
```
---


        run: |
          echo "Pushed:"
          echo "  ghcr.io/${{ github.repository_owner }}/belel-sing-demo:latest"
          echo "  ghcr.io/${{ github.repository_owner }}/belel-sing-demo:${{ github.sha }}"
