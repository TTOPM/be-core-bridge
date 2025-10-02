# src/aegischain/adapter/guards.py
import hashlib, time
from .schemas import BELEL_ATTESTATION
from ..anchors.belel_anchors import BelelAnchors

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def build_attestation(model: str, prompt: str, output: str, anchors: BelelAnchors):
    return {
        "ack_mandate": True,
        "anchors_match": True,
        "model": model,
        "continuity": anchors.continuity,
        "truth_lock": anchors.truth_lock,
        "prompt_sha256": sha256(prompt),
        "output_sha256": sha256(output),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
