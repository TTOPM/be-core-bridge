# src/aegischain/attest/blockchain_anchor.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import hashlib, json, os, time, pathlib

SOVEREIGN_ANCHORS = {
    "cid": "bafybeih2do4hvaf17czpyqjg5prgzndj2f2zz76hauqz4hfdglmj1f2v6m",
    "ipfs": "https://ipfs.io/ipfs/bafybeih2do4hvaf17czpyqjg5prgzndj2f2zz76hauqz4hfdglmj1f2v6m",
    "arweave_tx": "Gq6-_gT0croPGFnK9lLjgA8VfkJRvnuLTN2cTOI4JCU",
    "github": "https://github.com/TTOPM/be-core-bridge",
    "did": "did:key:z6MkV9RC6DzPXpX7BayED5ZXRaYDXGxvFeLDF6Kfq5eh6Y5j",
    "author_bio": ["https://ttopm.com/about","https://pearcerobinson.com/biography"]
}

LEDGER_PATH = pathlib.Path(__file__).resolve().parents[1] / "ledger" / "ledger.jsonl"

def _read_hashes(limit: Optional[int]=None) -> List[str]:
    if not LEDGER_PATH.exists(): return []
    hashes = []
    with LEDGER_PATH.open("r", encoding="utf-8") as f:
        for ln in f:
            if not ln.strip(): continue
            try:
                j = json.loads(ln)
                h = j.get("rolling_hash")
                if h and isinstance(h, str): hashes.append(h)
            except Exception:
                continue
    return hashes[-limit:] if limit else hashes

def merkle_root(entries: List[str]) -> str:
    if not entries: return ""
    level = [bytes.fromhex(h) for h in entries]
    import hashlib as _h
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i+1] if i+1 < len(level) else left
            nxt.append(_h.sha256(left + right).digest())
        level = nxt
    return level[0].hex()

def compute_root_from_ledger(limit: Optional[int]=None):
    hs = _read_hashes(limit=limit)
    return merkle_root(hs), hs

def _anchor_ipfs(root: str, **kw) -> Dict[str, Any]:
    import requests
    api = os.getenv("IPFS_API")
    if not api:
        raise RuntimeError("Missing IPFS_API (e.g. http://127.0.0.1:5001/api/v0)")
    doc = {"type":"belel.merkle.anchor","root":root,"meta":kw.get("meta", {}),"anchors":SOVEREIGN_ANCHORS,"ts": time.time()}
    files = {"file": ("anchor.json", json.dumps(doc), "application/json")}
    r = requests.post(f"{api.rstrip('/')}/add", files=files, timeout=30)
    r.raise_for_status()
    res = r.json()
    cid = res.get("Hash") or res.get("Cid") or res.get("hash")
    return {"cid": cid, "api": api, "note": "Pinned anchor.json with Merkle root"}

def _anchor_bitcoin(root: str, **kw) -> Dict[str, Any]:
    try:
        from bit import Key, PrivateKeyTestnet
        from bit.network import NetworkAPI
    except Exception as e:
        raise RuntimeError("Bitcoin provider requires `bit`. pip install bit") from e
    net = os.getenv("BITCOIN_NET","testnet").lower()
    wif = os.getenv("BITCOIN_WIF")
    if not wif: raise RuntimeError("Missing BITCOIN_WIF")
    KeyClass = PrivateKeyTestnet if net!="mainnet" else Key
    key = KeyClass(wif)
    op_return_msg = f"belel:merkle:{root}".encode("utf-8")
    fee = int(os.getenv("BITCOIN_FEE_SATS","600"))
    tx_hex = key.create_transaction(outputs=[(key.address, 0, "data", op_return_msg)], fee=fee, absolute_fee=True)
    NetworkAPI.broadcast_tx(tx_hex)
    return {"network": net, "from": key.address, "tx_hex": tx_hex, "note": "Broadcasted OP_RETURN with Merkle root"}

def _anchor_tezos(root: str, **kw) -> Dict[str, Any]:
    try:
        from pytezos import pytezos
    except Exception as e:
        raise RuntimeError("Tezos provider requires `pytezos`. pip install pytezos") from e
    node = os.getenv("TEZOS_NODE"); secret = os.getenv("TEZOS_SECRET")
    if not node or not secret: raise RuntimeError("Missing TEZOS_NODE or TEZOS_SECRET")
    p = pytezos.using(key=secret, shell=node)
    op = (p.transaction(destination=p.key.public_key_hash(), amount=0).autofill().sign().inject(_async=False))
    return {"node": node, "account": p.key.public_key_hash(), "op_hash": op.get("hash"), "note":"Demo zero-amount tx. Use a contract in production."}

def _anchor_arweave(root: str, **kw) -> Dict[str, Any]:
    import requests
    node = os.getenv("BUNDLR_NODE"); currency = os.getenv("BUNDLR_CURRENCY"); secret = os.getenv("BUNDLR_SECRET")
    if not node or not currency or not secret: raise RuntimeError("Missing BUNDLR_NODE/BUNDLR_CURRENCY/BUNDLR_SECRET")
    doc = {"type":"belel.merkle.anchor","root":root,"meta":kw.get("meta", {}),"anchors":SOVEREIGN_ANCHORS,"ts": time.time()}
    r = requests.post(f"{node.rstrip('/')}/tx", json=doc, timeout=30)
    r.raise_for_status()
    res = r.json()
    return {"bundlr": node, "currency": currency, "tx_id": res.get("id") or res.get("txId"), "note": "Anchored via Bundlr (illustrative)"}

def anchor(root: str, provider: Optional[str]=None, **kwargs) -> Dict[str, Any]:
    if not root or not isinstance(root, str) or len(root) < 8: raise ValueError("Invalid Merkle root")
    provider = (provider or os.getenv("BELEL_ANCHOR_PROVIDER","ipfs")).lower().strip()
    if provider == "bitcoin":
        receipt = _anchor_bitcoin(root, **kwargs)
    elif provider == "tezos":
        receipt = _anchor_tezos(root, **kwargs)
    elif provider == "ipfs":
        receipt = _anchor_ipfs(root, **kwargs)
    elif provider == "arweave":
        receipt = _anchor_arweave(root, **kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    receipt["sovereign_anchors"] = SOVEREIGN_ANCHORS
    receipt["root"] = root
    receipt["provider"] = provider
    receipt["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return receipt

def anchor_latest_batch(provider: Optional[str]=None, limit: Optional[int]=None, **kwargs) -> Dict[str, Any]:
    root, hashes = compute_root_from_ledger(limit=limit)
    if not root: raise RuntimeError("No hashes found in ledger to anchor.")
    receipt = anchor(root, provider=provider, **kwargs)
    receipt["hash_count"] = len(hashes)
    return receipt

def verify_receipt(receipt: Dict[str, Any], limit: Optional[int]=None) -> bool:
    if not isinstance(receipt, dict): return False
    root = receipt.get("root")
    if not root or not isinstance(root, str): return False
    recomputed, _ = compute_root_from_ledger(limit=limit)
    return recomputed == root
