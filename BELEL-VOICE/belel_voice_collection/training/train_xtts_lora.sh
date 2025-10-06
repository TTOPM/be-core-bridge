
#!/usr/bin/env bash
set -euo pipefail
# Simple wrapper for Coqui TTS trainer
# Make sure your JSONL is at data/belel_manifest.jsonl
tts train --config_path training/xtts_v2_lora.yaml
