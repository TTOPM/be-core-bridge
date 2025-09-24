#!/usr/bin/env python3
import argparse, hashlib, json, time, os, base64
from pathlib import Path

AUTH_DIR = Path.home()/".belel"
AUTH_DIR.mkdir(parents=True, exist_ok=True)
LOG = AUTH_DIR/"auth_log.jsonl"

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="Raw text to hash")
    ap.add_argument("--file", help="Path to file (image/video/pdf)")
    ap.add_argument("--source", help="Optional source URL")
    args = ap.parse_args()

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if args.text:
        digest = sha256_text(args.text)
        item = {"ts": ts, "kind": "text", "sha256": digest, "source": args.source or None}
    elif args.file:
        p = os.path.abspath(args.file)
        digest = sha256_file(p)
        item = {"ts": ts, "kind": "file", "path": p, "sha256": digest, "source": args.source or None}
    else:
        raise SystemExit("Provide --text or --file")

    with open(LOG, "a") as f:
        f.write(json.dumps(item)+"\n")
    print(json.dumps(item, indent=2))

if __name__ == "__main__":
    main()
