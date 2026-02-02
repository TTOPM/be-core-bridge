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

## 14) `.github/workflows/belel-sing-demo-deploy.yml`

This builds and pushes the demo container to **GHCR** on pushes to `main`, and can be extended to deploy to your host. (GitHub’s workflow rules require valid YAML and presence on default branch for events.)  [oai_citation:4‡GitHub Docs](https://docs.github.com/actions/using-workflows/about-workflows?utm_source=chatgpt.com)

```yaml
name: BELEL-SING Demo (Build + Push)

on:
  push:
    branches: [ "main" ]
    paths:
      - "BELEL-SING/demo_public/**"
      - ".github/workflows/belel-sing-demo-deploy.yml"
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  build_push:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          file: BELEL-SING/demo_public/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/belel-sing-demo:latest
            ghcr.io/${{ github.repository_owner }}/belel-sing-demo:${{ github.sha }}

      - name: Summary
        run: |
          echo "Pushed:"
          echo "  ghcr.io/${{ github.repository_owner }}/belel-sing-demo:latest"
          echo "  ghcr.io/${{ github.repository_owner }}/belel-sing-demo:${{ github.sha }}"
