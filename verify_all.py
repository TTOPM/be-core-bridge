import yaml, json, pathlib, os
from verifier.runners.verify_manifest import verify_manifest
from verifier.runners.verify_tweet_thread import verify_tweet_thread
from verifier.core.signer import sign_bundle
from verifier.core.canonical import canonical_json
from verifier.adapters.ipfs_client import pin_bytes_to_ipfs

CONFIG = pathlib.Path("config/targets.yaml")
OUTDIR = pathlib.Path("attestations")
OUTDIR.mkdir(exist_ok=True)

ENABLE_PIN = os.environ.get("ENABLE_IPFS_PIN", "0") in ("1","true","True","YES","yes")

def write_bundle(subject: str, bundle: dict):
    # sign if key present
    bundle = sign_bundle(bundle)

    # write file
    fn = f'{subject.replace(":","_")}.json'
    path = OUTDIR / fn
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2))

    # optional IPFS pin
    if ENABLE_PIN:
        data = canonical_json(bundle)
        ipfs_res = pin_bytes_to_ipfs(data)
        if ipfs_res.get("ok"):
            bundle["evidence_cid"] = ipfs_res["cid"]
            path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2))
        else:
            bundle["ipfs_error"] = ipfs_res.get("error","unknown")
            path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2))

    return {"subject": subject, "integrity_hash": bundle.get("integrity_hash"), "file": str(path), "cid": bundle.get("evidence_cid")}

def main():
    cfg = yaml.safe_load(CONFIG.read_text())
    index = []

    # GitHub manifests
    for item in cfg.get("github_manifests", []):
        b = verify_manifest(
            name=item["name"],
            file=item.get("file",""),
            raw=item.get("raw",""),
            html=item.get("html",""),
            ipfs=item.get("ipfs","")
        )
        index.append(write_bundle(b["subject"], b))

    # Tweet threads (optional)
    for item in cfg.get("tweet_threads", []):
        b = verify_tweet_thread(item["name"], item["status_url"])
        index.append(write_bundle(b["subject"], b))

    (OUTDIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(json.dumps(index, indent=2))

if __name__ == "__main__":
    main()
