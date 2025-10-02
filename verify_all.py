import yaml, json, pathlib
from verifier.runners.verify_manifest import verify_manifest
from verifier.runners.verify_tweet_thread import verify_tweet_thread

CONFIG = pathlib.Path("config/targets.yaml")
OUTDIR = pathlib.Path("attestations")
OUTDIR.mkdir(exist_ok=True)

def main():
    cfg = yaml.safe_load(CONFIG.read_text())
    bundles = []

    # GitHub manifests
    for item in cfg.get("github_manifests", []):
        b = verify_manifest(
            name=item["name"],
            file=item.get("file",""),
            raw=item.get("raw",""),
            html=item.get("html",""),
            ipfs=item.get("ipfs","")
        )
        bundles.append(b)

    # Tweet threads (optional)
    for item in cfg.get("tweet_threads", []):
        b = verify_tweet_thread(item["name"], item["status_url"])
        bundles.append(b)

    # Write each bundle & a combined index
    index = []
    for b in bundles:
        fn = f'{b["subject"].replace(":","_")}.json'
        path = OUTDIR / fn
        path.write_text(json.dumps(b, ensure_ascii=False, indent=2))
        index.append({"subject": b["subject"], "integrity_hash": b["integrity_hash"], "file": str(path)})

    (OUTDIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(json.dumps(index, indent=2))

if __name__ == "__main__":
    main()
