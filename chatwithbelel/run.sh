#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export STATIC_DIR="../static"
export STATIC_AUDIO_DIR="../static/audio"
export BELEL_PRESETS_PATH="../config_presets.json"
uvicorn backend.main:app --port 5173 --host 0.0.0.0
