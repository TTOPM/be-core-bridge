from __future__ import annotations
import os, json, requests, glob, hashlib

IPFS_API = os.getenv("IPFS_API","http://127.0.0.1:5001/api/v0")
ARWEAVE_ENDPOINT = os.getenv("ARWEAVE_ENDPOINT","https://arweave.net")  # placeholder

def pin_to_ipfs(path: str) -> str:
    with open(path,"rb") as f:
        resp = requests.post(f"{IPFS_API}/add", files={"file": f})
    resp.raise_for_status()
    return resp.json()["Hash"]

def post_to_arweave(path: str) -> str:
    # Placeholder: integrate Bundlr or Arweave SDK for signed tx
    digest = hashlib.sha256(open(path,"rb").read()).hexdigest()
    # Store digest to your public endpoint or leave as TODO
    return f"sha256:{digest}"

def snapshot_glob(pattern: str = "~/.grok/recovery/*.json") -> list[dict]:
    paths = glob.glob(os.path.expanduser(pattern))
    out=[]
    for p in paths:
        cid = pin_to_ipfs(p)
        ar = post_to_arweave(p)
        out.append({"file": p, "ipfs_cid": cid, "arweave": ar})
    return out

if __name__ == "__main__":
    print(json.dumps(snapshot_glob(), indent=2))
