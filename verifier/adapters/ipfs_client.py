import os, json

# ENV (optional):
#  - IPFS_API_MULTIADDR  (default: /ip4/127.0.0.1/tcp/5001/http)
#  - PINATA_JWT          (if present, uses Pinata pinning as fallback)

def pin_bytes_to_ipfs(data: bytes) -> dict:
    """
    Try local IPFS daemon first; fallback to Pinata if configured.
    Returns: {"ok":True,"cid":"..."} or {"ok":False,"error":"..."}
    """
    # 1) Local daemon via ipfshttpclient
    try:
        import ipfshttpclient
        addr = os.environ.get("IPFS_API_MULTIADDR", "/ip4/127.0.0.1/tcp/5001/http")
        with ipfshttpclient.connect(addr) as client:
            res = client.add_bytes(data)
            return {"ok": True, "cid": res}
    except Exception as e:
        err_local = str(e)

    # 2) Pinata fallback
    token = os.environ.get("PINATA_JWT", "").strip()
    if token:
        import requests
        try:
            r = requests.post(
                "https://api.pinata.cloud/pinning/pinFileToIPFS",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("bundle.json", data, "application/json")},
                timeout=30
            )
            if r.status_code in (200, 202):
                cid = r.json().get("IpfsHash") or r.json().get("ipfsHash")
                if cid:
                    return {"ok": True, "cid": cid}
            return {"ok": False, "error": f"Pinata error: {r.status_code} {r.text}"}
        except Exception as e:
            return {"ok": False, "error": f"Pinata exception: {e}"}

    return {"ok": False, "error": f"IPFS local failed: {err_local}; no Pinata fallback configured"}
