from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class LikenessCheckResult:
    allowed: bool
    reason: str = "ok"

def check_blp_likeness(image_bytes: bytes) -> LikenessCheckResult:
    """
    Stub: call Belel BLP likeness guard. Deny if matches sealed likeness and policy forbids upstreaming.
    Replace with your detector; keep the API shape.
    """
    # For now, pass through; wire to your real checker later.
    return LikenessCheckResult(True, "ok")

def build_multimodal_payload(
    model: str,
    prompt: str,
    images: List[bytes]
) -> Dict[str, Any]:
    """
    Package a Grok multimodal request; caller must attach Authorization header etc.
    """
    for img in images:
        lk = check_blp_likeness(img)
        if not lk.allowed:
            raise PermissionError(f"blp_blocked:{lk.reason}")

    content: List[Dict[str, Any]] = [{"type":"text","text":prompt}]
    for img in images:
        content.append({"type":"image","image": img})  # your transport layer may need base64

    return {"model": model, "messages":[{"role":"user","content":content}]}
