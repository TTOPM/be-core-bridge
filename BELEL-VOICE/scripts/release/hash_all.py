import hashlib, pathlib, json, datetime
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "dist"; OUT.mkdir(parents=True, exist_ok=True)
def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
entries = []
for p in ROOT.rglob("*"):
    if p.is_file() and "dist" not in p.parts:
        entries.append({"path": p.relative_to(ROOT).as_posix(), "sha256": sha256_of(p)})
(HASHES:=OUT / "HASHES.json").write_text(json.dumps({"generated": datetime.datetime.utcnow().isoformat()+"Z","files": entries}, indent=2))
print("Wrote", HASHES)
