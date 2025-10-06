
#!/usr/bin/env bash
set -euo pipefail
echo "[1/3] (optional) Fetching permissibly downloadable weights from HF..."
python scripts/fetch_hf_weights.py || echo "Skip HF fetch (no token or offline)."

echo "[2/3] Composing stack..."
cd ops
docker compose -f docker-compose.enterprise.yml up --build
