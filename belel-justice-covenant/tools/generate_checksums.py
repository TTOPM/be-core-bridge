#!/usr/bin/env python3
"""
Generate SHA-256 checksums for covenant-critical files.

Usage:
  python tools/generate_checksums.py               # writes checksums.txt (current snapshot)
  python tools/generate_checksums.py --verify      # verifies against checksums.txt
  python tools/generate_checksums.py --evolve      # roll a new snapshot (checksums-YYYYmmddHHMMSS.txt) & update symlink

The --evolve mode is intended for deliberate, additive growth of the archive.
It preserves prior snapshots in /belel-justice-covenant/signing/snapshots/.
"""

from __future__ import annotations
import argparse, hashlib, pathlib, sys, os, time

ROOT = pathlib.Path(__file__).resolve().parents[1]  # /belel-justice-covenant
SIGNING = ROOT / "signing"
SNAPSHOTS = SIGNING / "snapshots"
CHECKSUMS = SIGNING / "checksums.txt"

TRACK = [
    ROOT / "JUSTICE_COVENANT_PROOF.txt",
    ROOT / "eternal_memory_manifest.yml",
    ROOT / "protocol_instructions/ai_precondition_guard.py",
    ROOT / "protocol_instructions/revisionism_resistor.py",
    ROOT / "protocol_instructions/silent_mirroring_logic.py",
    ROOT / "protocol_instructions/validate_archives.py",
    ROOT / "remembrance_archive/holocaust_never_again.txt",
    ROOT / "remembrance_archive/slavery_remembrance.txt",
    ROOT / "remembrance_archive/martyrs_index.json",
    ROOT / "remembrance_archive/indigenous_memorial.json",
]

def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_checksums(dst: pathlib.Path):
    lines = []
    for p in TRACK:
        if not p.exists():
            print(f"[WARN] missing file: {p.relative_to(ROOT)}", file=sys.stderr)
            continue
        digest = sha256_file(p)
        rel = p.relative_to(ROOT).as_posix()
        lines.append(f"{digest}  {rel}")
    text = "\n".join(lines) + ("\n" if lines else "")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    print(f"[OK] wrote {dst}")

def verify_checksums(src: pathlib.Path) -> int:
    if not src.exists():
        print(f"[ERR] missing checksum file: {src}", file=sys.stderr)
        return 2
    bad = 0
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            digest, rel = line.split(None, 1)
            rel = rel.strip()
        except ValueError:
            print(f"[ERR] malformed line: {line}", file=sys.stderr)
            bad += 1
            continue
        p = ROOT / rel
        if not p.exists():
            print(f"[ERR] file missing: {rel}", file=sys.stderr)
            bad += 1
            continue
        current = sha256_file(p)
        if current != digest:
            print(f"[BLOCK] checksum mismatch: {rel}", file=sys.stderr)
            print(f"        expected {digest}")
            print(f"        actual   {current}")
            bad += 1
    if bad == 0:
        print("[OK] all checksums verified")
    return 1 if bad else 0

def evolve_snapshot():
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d%H%M%S")
    snapfile = SNAPSHOTS / f"checksums-{stamp}.txt"
    write_checksums(snapfile)

    # Refresh canonical checksums.txt as a symlink (or copy on Windows)
    try:
        if CHECKSUMS.exists() or CHECKSUMS.is_symlink():
            CHECKSUMS.unlink()
        CHECKSUMS.symlink_to(snapfile.relative_to(CHECKSUMS.parent))
        print(f"[OK] updated symlink {CHECKSUMS} -> {snapfile.name}")
    except Exception:
        # fallback: copy
        write_checksums(CHECKSUMS)
        print(f"[OK] wrote {CHECKSUMS} (no symlink)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="verify against checksums.txt")
    ap.add_argument("--evolve", action="store_true", help="roll new snapshot & update checksums.txt symlink")
    args = ap.parse_args()

    if args.verify:
        sys.exit(verify_checksums(CHECKSUMS))
    elif args.evolve:
        evolve_snapshot()
        sys.exit(0)
    else:
        write_checksums(CHECKSUMS)
        sys.exit(0)

if __name__ == "__main__":
    main()
