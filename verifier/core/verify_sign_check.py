import base64
from typing import Tuple, Dict, Any

from .canonical import canonical_json, sha256hex

# Returns: (ok, details)
def verify_bundle_signature(bundle: Dict[str, Any], pubkey_b64: str) -> Tuple[bool, Dict[str, str]]:
    """
    Verify Ed25519 signature on a bundle produced by verify_all.py.
    - Ensures the signature matches the canonicalized bundle.
    - Confirms msg_hash equals the sha256 of the canonicalized bundle.
    """
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError
    except Exception as e:
        return False, {"error": f"PyNaCl not available: {e}"}

    sig_block = bundle.get("verifier_sig")
    if not sig_block:
        return False, {"error": "bundle has no verifier_sig"}

    sig_b64 = sig_block.get("sig_b64")
    msg_hash = sig_block.get("msg_hash")
    claimed_pub_b64 = sig_block.get("pubkey_b64")

    if not sig_b64 or not msg_hash:
        return False, {"error": "verifier_sig missing sig_b64 or msg_hash"}

    # Optional: if a pubkey is included in the bundle, ensure it matches supplied one
    if claimed_pub_b64 and pubkey_b64 and claimed_pub_b64 != pubkey_b64:
        return False, {"error": "pubkey mismatch", "bundle_pub": claimed_pub_b64, "supplied_pub": pubkey_b64}

    try:
        pubkey_bytes = base64.b64decode(pubkey_b64)
        sig_bytes = base64.b64decode(sig_b64)
    except Exception as e:
        return False, {"error": f"invalid base64: {e}"}

    # Canonicalize the *entire* bundle (including verifier_sig) minus verifier_sig for signing?
    # We signed the full bundle content in verify_all.py BEFORE adding verifier_sig? No — we signed the canonical bundle as-is and then attached sig.
    # In verify_all.py, sign_bundle() signs canonical_json(bundle) where bundle does NOT yet contain verifier_sig.
    # So we must reconstruct that same pre-sig message by cloning and removing verifier_sig.
    bundle_copy = dict(bundle)
    bundle_copy.pop("verifier_sig", None)
    message = canonical_json(bundle_copy)
    calc_hash = "sha256:" + sha256hex(message)

    if calc_hash != msg_hash:
        return False, {"error": "msg_hash mismatch", "expected": calc_hash, "claimed": msg_hash}

    try:
        VerifyKey(pubkey_bytes).verify(message, sig_bytes)
        return True, {"msg_hash": msg_hash}
    except BadSignatureError:
        return False, {"error": "bad signature"}
    except Exception as e:
        return False, {"error": f"verify exception: {e}"}

import os, json, pathlib, sys
from verifier.core.verify_sign_check import verify_bundle_signature

ATTN_DIR = pathlib.Path("attestations")

def load_pubkey():
    # 1) ENV takes precedence
    env_pub = os.environ.get("ED25519_PUB_B64", "").strip()
    if env_pub:
        return env_pub

    # 2) keys/public.json fallback
    keys_file = pathlib.Path("keys/public.json")
    if keys_file.exists():
        try:
            data = json.loads(keys_file.read_text())
            pub = data.get("ed25519_pub_b64","").strip()
            if pub:
                return pub
        except Exception:
            pass

    print("No ED25519 public key found. Set ED25519_PUB_B64 or create keys/public.json.", file=sys.stderr)
    sys.exit(2)

def main():
    pub = load_pubkey()
    if not ATTN_DIR.exists():
        print("No attestations/ directory found.", file=sys.stderr)
        sys.exit(2)

    files = sorted(ATTN_DIR.glob("*.json"))
    if not files:
        print("No JSON bundles found in attestations/.", file=sys.stderr)
        sys.exit(2)

    failed = 0
    for f in files:
        try:
            bundle = json.loads(f.read_text())
        except Exception as e:
            print(f"[FAIL] {f.name}: invalid JSON ({e})")
            failed += 1
            continue

        ok, info = verify_bundle_signature(bundle, pub)
        if ok:
            print(f"[OK]   {f.name}  {info.get('msg_hash','')}")
        else:
            print(f"[FAIL] {f.name}  {info}")
            failed += 1

    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
