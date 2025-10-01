# SPDX-License-Identifier: Belel-Protocol-1.0
from __future__ import annotations
import json, hashlib, pathlib
from typing import Dict, Any

def load_local_manifest(path="src/grok/MANIFEST_ANCHOR.json") -> Dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text())

def verify_local_files(m: Dict[str, Any], root="src/grok") -> bool:
    ok=True
    for f in m["files"]:
        p=pathlib.Path(root)/f["path"]
        h=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        if h!=f["sha256"]:
            ok=False
            break
    return ok
