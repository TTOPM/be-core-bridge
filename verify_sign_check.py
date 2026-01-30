#!/usr/bin/env python3
import os
import json
import pathlib
import sys
from typing import Optional, Tuple

from verifier.core.verify_sign_check import verify_bundle_signature

ATTN_DIR = pathlib.Path("attestations")
DEFAULT_KEYS_FILE = pathlib.Path("keys/public.json")


def _b64ish(s: str) -> bool:
    # lightweight sanity check (does not validate base64 fully)
    if not s:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=_-")
    return all(ch in allowed for ch in s) and len(s) >= 16


def load_pubkey() -> Tuple[Optional[str], str]:
    """
    Returns (pubkey_b64_or_none, source_label).

    Behavior:
    - If ED25519_PUB_B64 is set, use it.
    - Else try keys/public.json -> {"ed25519_pub_b64": "..."}.
    - If still missing:
        - If ALLOW_MISSING_PUBKEY=1, return (None, "missing-allowed").
        - Else exit(2).
    """
    env_pub = os.environ.get("ED25519_PUB_B64", "").strip()
    if env_pub:
        if not _b64ish(env_pub):
            print("ED25519_PUB_B64 is set but does not look like base64/urlsafe base64.", file=sys.stderr)
            sys.exit(2)
        return env_pub, "env:ED25519_PUB_B64"

    if DEFAULT_KEYS_FILE.exists():
        try:
            data = json.loads(DEFAULT_KEYS_FILE.read_text(encoding="utf-8"))
            pub = (data.get("ed25519_pub_b64") or "").strip()
            if pub:
                if not _b64ish(pub):
                    print("keys/public.json has ed25519_pub_b64 but it does not look like base64/urlsafe base64.", file=sys.stderr)
                    sys.exit(2)
                return pub, f"file:{DEFAULT_KEYS_FILE}"
        except Exception as e:
            print(f"Failed reading {DEFAULT_KEYS_FILE}: {e}", file=sys.stderr)
            sys.exit(2)

    if os.environ.get("ALLOW_MISSING_PUBKEY", "0") in ("1", "true", "True", "YES", "yes"):
        return None, "missing-allowed"

    print(
        "No ED25519 public key found.\n"
        "Set ED25519_PUB_B64 or create keys/public.json with {\"ed25519_pub_b64\":\"...\"}.\n"
        "If you intentionally want to skip signature verification in CI, set ALLOW_MISSING_PUBKEY=1.",
        file=sys.stderr
    )
    sys.exit(2)


def iter_bundles(attn_dir: pathlib.Path):
    """
    Yield JSON bundle paths to verify.
    Skips index.json by default.
    """
    for p in sorted(attn_dir.glob("*.json")):
        if p.name.lower() == "index.json":
            continue
        yield p


def main() -> None:
    pub, source = load_pubkey()
    print(f"[KEY] Public key source: {source}")

    if not ATTN_DIR.exists():
        print("No attestations/ directory found.", file=sys.stderr)
        sys.exit(2)

    files = list(iter_bundles(ATTN_DIR))
    if not files:
        print("No JSON bundles found in attestations/ (excluding index.json).", file=sys.stderr)
        sys.exit(2)

    # If we allowed missing key, we can only do structural checks.
    if pub is None:
        print("[WARN] No public key available. Running structural-only checks.")
        failed = 0
        for f in files:
            try:
                bundle = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[FAIL] {f.name}: invalid JSON ({e})")
                failed += 1
                continue

            # Structural checks that are safe and useful
            subject = bundle.get("subject", "")
            integrity_hash = bundle.get("integrity_hash", "")
            if not subject or not integrity_hash:
                print(f"[FAIL] {f.name}: missing required fields (subject/integrity_hash)")
                failed += 1
            else:
                print(f"[OK]   {f.name}  structural")
        sys.exit(0 if failed == 0 else 1)

    # Full signature verification
    failed = 0
    for f in files:
        try:
            bundle = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[FAIL] {f.name}: invalid JSON ({e})")
            failed += 1
            continue

        try:
            ok, info = verify_bundle_signature(bundle, pub)
        except Exception as e:
            print(f"[FAIL] {f.name}: verifier exception ({e})")
            failed += 1
            continue

        if ok:
            msg_hash = ""
            if isinstance(info, dict):
                msg_hash = info.get("msg_hash", "") or info.get("integrity_hash", "") or ""
            print(f"[OK]   {f.name}  {msg_hash}")
        else:
            print(f"[FAIL] {f.name}  {info}")
            failed += 1

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
