import json, hashlib, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
HASHES = DIST / "HASHES.json"
if not HASHES.exists():
    raise SystemExit("Run `make hash` first.")
data = json.loads(HASHES.read_text())
digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
manifest = {
    "name": "BELEL-LEX Gold Standard Stack",
    "version": "0.1.0",
    "generated": datetime.datetime.utcnow().isoformat()+"Z",
    "hashes_sha256": digest,
    "hashes_file": "HASHES.json",
    "license": "BPSL v1.0",
    "integrity_note": "Replace with real signing (minisign/sigstore) for prod"
}
(DIST / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2))
print("Wrote", DIST / "RELEASE_MANIFEST.json")
