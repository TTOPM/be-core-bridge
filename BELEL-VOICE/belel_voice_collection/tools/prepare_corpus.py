
import argparse, os, json, random
from pathlib import Path
from dataclasses import dataclass, asdict

# We use HF datasets if available, but we don't hardcode non-existent repos.
try:
    from datasets import load_dataset, Audio, concatenate_datasets
    _HF = True
except Exception:
    _HF = False

@dataclass
class Sample:
    audio_path: str
    text: str
    speaker_id: str = "spk0"
    language: str = "en"

def save_manifest(samples, out_path):
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        for s in samples:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")
    print(f"Wrote {len(samples)} entries -> {out_path}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data/belel_manifest.jsonl')
    ap.add_argument('--max_per_ds', type=int, default=1000, help='Cap per dataset to keep things light.')
    ap.add_argument('--langs', default='en,es,fr,de,zh', help='Language codes to include when supported.')
    ap.add_argument('--local_wavs', default=None, help='Optional folder of local wavs with a transcript.txt (audio\ttext).')
    args = ap.parse_args()

    samples = []

    # Optionally harvest local wavs (recommended for cloning)
    if args.local_wavs and os.path.isdir(args.local_wavs):
        txt = os.path.join(args.local_wavs, 'transcript.txt')
        if os.path.exists(txt):
            for line in open(txt, 'r', encoding='utf-8'):
                wav, text = line.strip().split('\t', 1)
                samples.append(Sample(audio_path=os.path.join(args.local_wavs, wav), text=text))

    # Example public datasets (safe, widely-available). We keep small caps by default.
    if _HF:
        try:
            cv = load_dataset('mozilla-foundation/common_voice_17_0', 'en', split=f'train[:{args.max_per_ds}]')
            cv = cv.cast_column('audio', Audio(sampling_rate=22050))
            for row in cv:
                if row.get('sentence') and row.get('audio') and row['audio'].get('path'):
                    samples.append(Sample(audio_path=row['audio']['path'], text=row['sentence'], language='en'))
        except Exception as e:
            print('Common Voice not available in this environment:', e)

    random.shuffle(samples)
    save_manifest(samples, args.out)

if __name__ == '__main__':
    main()
