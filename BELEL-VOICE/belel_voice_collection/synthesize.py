
import argparse, os, soundfile as sf, torch
from pathlib import Path

# Parler-TTS (transformers)
try:
    from transformers import AutoProcessor
    from parler_tts import ParlerTTSForConditionalGeneration
    _PARLER_AVAILABLE = True
except Exception:
    _PARLER_AVAILABLE = False

# Coqui TTS (XTTS v2)
try:
    from TTS.api import TTS
    _COQUI_AVAILABLE = True
except Exception:
    _COQUI_AVAILABLE = False

import json

def load_config(cfg_path):
    with open(cfg_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_voice(cfg, name):
    for v in cfg["voices"]:
        if v["name"] == name:
            return v
    raise SystemExit(f"Voice '{name}' not found in config.")

def gen_parler(model_id, text, style_text, out_wav):
    if not _PARLER_AVAILABLE:
        raise SystemExit("Parler-TTS packages not installed. pip install transformers parler-tts")
    processor = AutoProcessor.from_pretrained(model_id)
    model = ParlerTTSForConditionalGeneration.from_pretrained(model_id)
    inputs = processor(text=text, speaker_prompt=style_text, return_tensors="pt")
    with torch.no_grad():
        waveform = model.generate(**inputs).waveform  # Parler returns an object with .waveform
    audio = waveform.squeeze().cpu().numpy()
    sf.write(out_wav, audio, 22050)
    return out_wav

def gen_xtts(model_id, text, style_text, samples, out_wav, language=None):
    if not _COQUI_AVAILABLE:
        raise SystemExit("Coqui TTS not installed. pip install TTS")
    tts = TTS(model_id)
    speaker_wavs = [s for s in samples if os.path.exists(s)] if samples else None
    # XTTS v2: if cloning, pass speaker_wav(s); else fallback to default speaker
    if speaker_wavs:
        audio = tts.tts(text=text, speaker_wav=speaker_wavs[0], language=language or "en")
    else:
        audio = tts.tts(text=text, language=language or "en")
    sf.write(out_wav, audio, 22050)
    return out_wav

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='voices.json')
    ap.add_argument('--voice', required=True)
    ap.add_argument('--text', required=True)
    ap.add_argument('--language', default=None, help="Language hint for XTTS (e.g., 'en','es','fr','zh')")
    ap.add_argument('--out', default='out.wav')
    args = ap.parse_args()

    cfg = load_config(args.config)
    voice = find_voice(cfg, args.voice)
    backend = cfg["backends"][voice["backend"]]

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)

    if voice["backend"] == "parler_tts":
        gen_parler(backend["model_id"], args.text, voice["style_text"], args.out)
    elif voice["backend"] == "xtts_v2":
        gen_xtts(backend["model_id"], args.text, voice["style_text"], voice.get("speaker_samples", []), args.out, args.language)
    elif voice["backend"] == "bark_small":
        # Minimal example using Bark via transformers pipeline
        from transformers import AutoProcessor, BarkModel
        import numpy as np, torch
        processor = AutoProcessor.from_pretrained(backend["model_id"])
        model = BarkModel.from_pretrained(backend["model_id"])
        inputs = processor(text=args.text).to(model.device)
        with torch.no_grad():
            audio_array = model.generate(**inputs).cpu().numpy().squeeze()
        sf.write(args.out, audio_array, model.generation_config.sample_rate)
    else:
        raise SystemExit(f"Unsupported backend: {voice['backend']}")

    print(f"Wrote: {args.out}")

if __name__ == '__main__':
    main()
