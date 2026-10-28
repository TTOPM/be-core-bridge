#!/usr/bin/env python3
"""Check that uploading the BAIN archive would overwrite ZERO existing files.

Run from anywhere, pointing at the unzipped package root and repository root.
No filesystem mutation, no network, no git operations.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

SKIP={'.DS_Store','__pycache__'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',required=True)
    parser.add_argument('--package',required=True)
    args=parser.parse_args()
    repo=Path(args.destination).expanduser().resolve()
    bundle=Path(args.package).expanduser().resolve()
    if not repo.is_dir() or not bundle.is_dir():
        raise SystemExit('Both --destination and --package must be existing directories')
    if repo == bundle or repo in bundle.parents or bundle in repo.parents:
        raise SystemExit('Do not compare a directory against itself or a nested directory')
    conflicts=[]; count=0
    for f in bundle.rglob('*'):
        if not f.is_file() or any(part in SKIP for part in f.parts) or f.suffix == '.pyc': continue
        rel=f.relative_to(bundle)
        dest=repo/rel
        count+=1
        if dest.exists() or dest.is_symlink(): conflicts.append(str(rel))
    print(f'BAIN additive check: {count} files inspected')
    if conflicts:
        print('BLOCKED: existing destination files would be overwritten:')
        for path in conflicts: print(f'  - {path}')
        return 1
    print('PASS: no existing destination files would be overwritten')
    return 0

if __name__=='__main__': sys.exit(main())
