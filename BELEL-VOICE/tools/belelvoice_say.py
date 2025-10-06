#!/usr/bin/env python3
import argparse, json, base64, pathlib, sys
import requests

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--voice", default="en_GB")
    ap.add_argument("--engine", default="piper", choices=["piper","xtts","riva"])
    ap.add_argument("--clone_ref", default=None)
    ap.add_argument("--out", default="out.wav")
    ap.add_argument("--gateway", default="http://localhost:8000")
    args = ap.parse_args()
    payload = {
        "text": args.text,
        "voice": args.voice,
        "engine": args.engine,
        "clone_ref": args.clone_ref,
        "require_disclosure": True,
        "jurisdiction": "EU"
    }
    r = requests.post(f"{args.gateway}/v1/tts/synthesize", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    # In production, API should return binary or a URL; here we assume file path in "audio_ref"
    ref = data.get("audio_ref")
    if ref and ref.startswith("file://"):
        path = ref[len("file://"):]
        pathlib.Path(args.out).write_bytes(pathlib.Path(path).read_bytes())
        print("Saved:", args.out)
    else:
        # If bytes are returned (future), decode here
        print("Response:", json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
