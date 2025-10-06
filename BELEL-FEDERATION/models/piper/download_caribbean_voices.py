#!/usr/bin/env python3
Download an open Piper voice approximating Caribbean English.
Uses public Piper releases; select en_GB/en_US voices with warmer prosody until a true Caribbean model is added.

import argparse, os, sys, pathlib, urllib.request, shutil

VOICES = [
    # Fallback chain (public Piper release assets; URLs are examples and may change)
    ("en_GB-sean-medium.onnx", "https://github.com/rhasspy/piper/releases/download/2024.07.0/en_GB-sean-medium.onnx"),
    ("en_US-amy-medium.onnx", "https://github.com/rhasspy/piper/releases/download/2024.07.0/en_US-amy-medium.onnx"),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="models/piper")
    args = ap.parse_args()
    dest = pathlib.Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    for name, url in VOICES:
        out = dest / name
        if out.exists():
            print("Already present:", out)
            continue
        print("Downloading:", name)
        try:
            with urllib.request.urlopen(url) as r, open(out, "wb") as f:
                shutil.copyfileobj(r, f)
            print("Saved:", out)
        except Exception as e:
            print("Failed to download", name, "from", url, "->", e)
    print("Done. Place any additional Caribbean-accent voices here when available.")
if __name__ == "__main__":
    main()
