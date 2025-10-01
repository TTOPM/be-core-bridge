# SPDX-License-Identifier: Belel-Protocol-1.0
# © 2025 Pearce Robinson. All rights reserved.

from __future__ import annotations
import os, hashlib, base64, imghdr, logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from grok.grok_link_fetcher import LinkFetcher
from grok.grok_observability import audit_log

LOG = logging.getLogger("grok.multimodal")
LOG.setLevel(logging.INFO)

# Configurable rule source + defaults
BLP_RULE_URL = os.getenv(
    "BLP_RULE_URL",
    "https://raw.githubusercontent.com/TTOPM/be-core-bridge/main/blp_rules.json"
)
B64_ENCODE_IMAGES = os.getenv("GROK_MM_B64", "1") not in ("0", "false", "False")
DEFAULT_MAX_BYTES = int(os.getenv("BLP_MAX_BYTES", "10485760"))  # 10MB default
DEFAULT_MIME_ALLOW = set(
    (os.getenv("BLP_MIME_ALLOW", "jpeg,png,webp")).lower().split(",")
)

@dataclass
class LikenessCheckResult:
    allowed: bool
    reason: str = "ok"

def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _sniff_mime(b: bytes) -> str:
    # imghdr returns "jpeg", "png", "webp", etc. Good enough for pre-checks.
    kind = imghdr.what(None, h=b)
    return (kind or "octet-stream").lower()

def _load_rules() -> Optional[Dict[str, Any]]:
    fx = LinkFetcher().fetch_json(BLP_RULE_URL)
    if not fx or not fx.ok or fx.json_data is None:
        LOG.warning("BLP rules fetch failed from %s", BLP_RULE_URL)
        audit_log("blp_rules_fetch_failed", {"url": BLP_RULE_URL})
        return None
    return fx.json_data

def check_blp_likeness(image_bytes: bytes) -> LikenessCheckResult:
    """
    Validates an image against Belel Likeness Protocol (BLP) rules.
    Rules schema (all optional, non-breaking):
      {
        "allow_hashes": ["sha256...", ...],
        "deny_hashes":  ["sha256...", ...],
        "max_bytes": 10485760,
        "mime_allow": ["jpeg","png","webp"]
      }
    """
    rules = _load_rules()
    if rules is None:
        # Conservative fallback: allow, but log. Keep your previous behavior.
        return LikenessCheckResult(True, "rules_unavailable_allow")

    allow = set(rules.get("allow_hashes", []))
    deny  = set(rules.get("deny_hashes", []))
    max_bytes = int(rules.get("max_bytes", DEFAULT_MAX_BYTES))
    mime_allow = set(m.lower() for m in rules.get("mime_allow", list(DEFAULT_MIME_ALLOW)))

    h = _sha256(image_bytes)
    mime = _sniff_mime(image_bytes)
    size = len(image_bytes)

    # Size guard
    if size > max_bytes:
        audit_log("blp_block_size_exceeded", {"sha256": h, "size": size, "max": max_bytes})
        return LikenessCheckResult(False, "size_exceeded")

    # MIME guard
    if mime_allow and mime not in mime_allow:
        audit_log("blp_block_mime", {"sha256": h, "mime": mime, "allow": sorted(mime_allow)})
        return LikenessCheckResult(False, "mime_forbidden")

    # Explicit deny takes precedence
    if h in deny:
        audit_log("blp_block_hash_deny", {"sha256": h})
        return LikenessCheckResult(False, "hash_denied")

    # If allow list provided, require membership
    if allow and (h not in allow):
        audit_log("blp_block_hash_unlisted", {"sha256": h})
        return LikenessCheckResult(False, "hash_unlisted")

    audit_log("blp_ok", {"sha256": h, "mime": mime, "size": size})
    return LikenessCheckResult(True, "ok")

def _encode_image_payload(img: bytes) -> Dict[str, Any]:
    """
    Grok-compatible image part.
    If B64_ENCODE_IMAGES=1 (default), embed as base64 data URL-like object:
      {"type":"image","image":{"b64":"...","mime":"jpeg"}}
    Otherwise, pass raw bytes (your transport must handle it).
    """
    if B64_ENCODE_IMAGES:
        mime = _sniff_mime(img)
        return {
            "type": "image",
            "image": {
                "b64": base64.b64encode(img).decode("ascii"),
                "mime": mime
            }
        }
    else:
        # Original passthrough shape from your stub
        return {"type": "image", "image": img}

def build_multimodal_payload(
    model: str,
    prompt: str,
    images: List[bytes]
) -> Dict[str, Any]:
    """
    Package a Grok multimodal request; caller must attach Authorization header, etc.
    Enforces BLP likeness rules per image before packaging.
    """
    for img in images:
        lk = check_blp_likeness(img)
        if not lk.allowed:
            raise PermissionError(f"blp_blocked:{lk.reason}")

    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for img in images:
        content.append(_encode_image_payload(img))  # b64 or raw, per env flag

    return {"model": model, "messages": [{"role": "user", "content": content}]}
