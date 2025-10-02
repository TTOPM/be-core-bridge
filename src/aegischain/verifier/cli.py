# src/aegischain/verifier/cli.py
import json, sys, hashlib

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m aegischain.verifier.cli <attestation.json>")
        sys.exit(1)
    path = sys.argv[1]
    att = json.load(open(path))
    # minimal check: presence of origin fields
    required = ["openai_response_id","openai_system_fingerprint","openai_created"]
    ok = all(k in att.get("attestation", {}) for k in required)
    print(json.dumps({"ok": ok, "missing": [k for k in required if k not in (att.get('attestation') or {})]}, indent=2))

if __name__ == "__main__":
    main()
