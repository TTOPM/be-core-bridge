#!/usr/bin/env python3
import argparse, hashlib, sys, pathlib

def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="verify JSON against checksum file")
    ap.add_argument("json_path")
    ap.add_argument("checksum_path", nargs="?")
    args = ap.parse_args()

    j = pathlib.Path(args.json_path)
    if not j.exists():
        print(f"[!] missing {j}"); sys.exit(1)

    digest = sha256(j)

    if args.verify:
        if not args.checksum_path:
            print("[!] provide checksum file for --verify"); sys.exit(1)
        c = pathlib.Path(args.checksum_path)
        if not c.exists():
            print(f"[!] missing checksum {c}"); sys.exit(1)
        expected = c.read_text().strip().split()[0]
        ok = (digest == expected) or (digest in c.read_text())
        print(("[OK]" if ok else "[FAIL]"), j.name, digest)
        sys.exit(0 if ok else 2)
    else:
        print(f"{digest}  {j}")
