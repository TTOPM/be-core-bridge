
import argparse, json, os, numpy as np, librosa, torch
from pathlib import Path
from statistics import mean
from jiwer import wer
from transformers import WhisperProcessor, WhisperForConditionalGeneration

def transcribe_whisper(audio_path, model_id='openai/whisper-large-v3', device=None):
    processor = WhisperProcessor.from_pretrained(model_id)
    model = WhisperForConditionalGeneration.from_pretrained(model_id)
    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model.to(device)
    audio, sr = librosa.load(audio_path, sr=16000)
    inputs = processor(audio, sampling_rate=16000, return_tensors='pt').to(device)
    pred_ids = model.generate(**inputs)
    text = processor.batch_decode(pred_ids, skip_special_tokens=True)[0]
    return text.strip()

def pitch_energy_stats(audio_path):
    y, sr = librosa.load(audio_path, sr=22050)
    # Pitch via librosa.pyin (robust) - returns f0 with NaNs for unvoiced
    f0, vflag, _ = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
    f0 = f0[~np.isnan(f0)]
    pitch_var = float(np.std(f0)) if f0.size else 0.0
    # Energy via RMS
    rms = librosa.feature.rms(y=y).squeeze()
    energy_var = float(np.std(rms)) if rms.size else 0.0
    return pitch_var, energy_var

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', default='data/belel_manifest_eval.jsonl', help='JSONL with audio_path and text for evaluation.')
    ap.add_argument('--whisper_model', default='openai/whisper-large-v3')
    args = ap.parse_args()

    refs, hyps = [], []
    pvars, evars = [], []

    if not os.path.exists(args.manifest):
        raise SystemExit(f"Missing eval manifest: {args.manifest}")

    with open(args.manifest, 'r', encoding='utf-8') as f:
        for line in f:
            ex = json.loads(line)
            audio = ex['audio_path']
            ref_text = ex.get('text', '').strip()
            hyp = transcribe_whisper(audio, model_id=args.whisper_model)
            refs.append(ref_text)
            hyps.append(hyp)
            pv, ev = pitch_energy_stats(audio)
            pvars.append(pv); evars.append(ev)

    overall_wer = wer(refs, hyps)
    print('\n=== EVALUATION ===')
    print(f'WER: {overall_wer:.4f}')
    print(f'Pitch variance (mean): {mean(pvars):.4f}')
    print(f'Energy variance (mean RMS std): {mean(evars):.6f}')

if __name__ == '__main__':
    main()
