import json, os, pathlib, datetime, hashlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
HASHES = DIST / "HASHES.json"
DIST.mkdir(parents=True, exist_ok=True)
if not HASHES.exists():
    raise SystemExit("Run `make hash` first.")
with open(HASHES, "r") as f:
    data = json.load(f)
# Simple signature: hash of the hashes file (placeholder for real signing)
digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
manifest = {
    "name": "BELEL-MED Gold Standard Stack",
    "version": "0.1.0",
    "generated": datetime.datetime.utcnow().isoformat()+"Z",
    "hashes_sha256": digest,
    "hashes_file": "HASHES.json",
    "license": "BPSL v1.0",
    "canonical_anchor": "TTOPM/be-core-bridge",
    "integrity_note": "Replace with real signing (e.g., minisign/sigstore) for production"
}
with open(DIST / "RELEASE_MANIFEST.json", "w") as f:
    json.dump(manifest, f, indent=2)
print("Wrote", DIST / "RELEASE_MANIFEST.json")
