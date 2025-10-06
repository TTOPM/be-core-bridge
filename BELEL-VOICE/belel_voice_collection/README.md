
# Belel Voice Collection — Fixed & Practical

This drop makes the collection **run-able** and **sane** by grounding on widely available models and removing fictional APIs.

## Checkpoints (tested, real)
- **Parler-TTS (mini v1)**: `parler-tts/parler-tts-mini-v1` (style text prompts)
- **Coqui XTTS v2**: `tts_models/multilingual/multi-dataset/xtts_v2` (multilingual + voice cloning via reference WAVs)
- **Bark Small**: `suno/bark-small` (fast, expressive baseline)
- **Whisper Large v3 (STT)**: `openai/whisper-large-v3`

> You can swap/add backends in `voices.json` → `backends`.

## Install
```bash
pip install -U torch torchaudio soundfile datasets transformers TTS
# Parler-TTS requires the 'parler-tts' package (pip)
pip install parler-tts
```

## Quick Synthesis
Put your reference samples under `samples/`. Then:
```bash
python synthesize.py --config voices.json --voice belel_serene --text "Rise and shine. Let's build something great today." --out out_serene.wav
python synthesize.py --config voices.json --voice belel_resolve --text "We deliver. On time. Every time." --out out_resolve.wav
# Multilingual (XTTS), give language hint:
python synthesize.py --config voices.json --voice belel_multilingual --language fr --text "Bonjour tout le monde." --out out_multi.wav
```

## Data Prep (optional, for finetuning later)
Produces a **JSONL manifest** (audio_path, text, speaker_id, language).
```bash
python tools/prepare_corpus.py --out data/belel_manifest.jsonl --max_per_ds 200
```

## Notes on Finetuning
- **XTTS v2**: Use Coqui TTS training scripts with the JSONL manifest. Start with LoRA/partial finetune for speed.
- **Parler-TTS**: Community finetuning exists but is heavier; consider prompt-engineering styles first.

## Prosody & Style
- Parler-TTS accepts a `speaker_prompt` (we pass the voice's `style_text`).
- XTTS v2 supports voice cloning via `speaker_wav` and language hints.

## What changed vs. your draft
- Removed non-existent repos and placeholder losses (e.g., `index-tts-2`, custom prosody losses).
- Standardized schema (`voices.json`) and added a tiny **schema** file you can validate against.
- Provided a clean **synthesize.py** that runs offline if models are cached.
- Kept the "14 voices" concept scalable—add more entries copying the existing patterns.


---

## XTTS v2 LoRA Finetuning (Coqui)
1) Build a manifest from your data:
```bash
python tools/prepare_corpus.py --out data/belel_manifest.jsonl --max_per_ds 200
```
2) Train:
```bash
bash training/train_xtts_lora.sh
# or
python training/train_xtts_lora.py
```
3) The LoRA checkpoints will be in `training/outputs/xtts_v2_lora`.
   Integrate them by loading XTTS and applying LoRA weights per Coqui docs.

## Tiny Evaluation
Prepare an eval manifest with synthesized audio and target text:
```bash
# JSONL lines: {"audio_path": "synth/clip_001.wav", "text": "reference text ..."}
python tools/evaluate_tts.py --manifest data/belel_manifest_eval.jsonl
```
Reports:
- **WER** via Whisper-large-v3
- **Pitch variance** (std dev of f0 via `librosa.pyin`)
- **Energy variance** (std dev of RMS)
