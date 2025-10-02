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
