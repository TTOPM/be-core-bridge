# attest/blockchain_anchor.py
"""
Blockchain anchoring utilities for the Belel ↔ OpenAI Tri-Layer.

What this module provides:
- Merkle utilities over your rolling ledger hashes.
- A single `anchor(root, provider=...)` dispatcher returning a provider-specific receipt.
- Optional providers:
    * "ipfs"    : Pin a small JSON doc via IPFS HTTP API.
    * "bitcoin" : Broadcast OP_RETURN with root (requires `bit` library; testnet by default).
    * "tezos"   : (Demo) send a zero-amount tx or call a contract with `pytezos`.
    * "arweave" : (Illustrative) upload via Bundlr HTTP API (use official SDK in prod).

- Sovereign Identity Anchors are attached to each receipt for audit traceability.
- Helpers to compute a Merkle root from `attest/ledger.jsonl` and to anchor batches.
- A lightweight `verify_receipt()` to cross-check the receipt against the ledger.

Safety:
- Use testnets first; never commit secrets.
- All providers are lazy/optional; you'll get clear errors if an SDK/env var is missing.
"""

from __future__ import annotations
from typing import List, Dict, Any, Iterable, Optional, Tuple
import hashlib
import json
import os
import pathlib
import time

# ---------------- Sovereign Identity Anchors (immutable references) ----------------

SOVEREIGN_ANCHORS: Dict[str, Any] = {
    "cid": "bafybeih2do4hvaf17czpyqjg5prgzndj2f2zz76hauqz4hfdglmj1f2v6m",
    "ipfs": "https://ipfs.io/ipfs/bafybeih2do4hvaf17czpyqjg5prgzndj2f2zz76hauqz4hfdglmj1f2v6m",
    "arweave_tx": "Gq6-_gT0croPGFnK9lLjgA8VfkJRvnuLTN2cTOI4JCU",
    "github": "https://github.com/TTOPM/be-core-bridge",
    "did": "did:key:z6MkV9RC6DzPXpX7BayED5ZXRaYDXGxvFeLDF6Kfq5eh6Y5j",
    "author_bio": [
        "https://ttopm.com/about",
        "https://pearcerobinson.com/biography",
    ],
}

# ---------------- Ledger I/O ----------------

LEDGER_PATH = pathlib.Path(__file__).resolve().parent / "ledger.jsonl"


def _read_rolling_hashes_from_ledger(limit: Optional[int] = None) -> List[str]:
    """Read 'rolling_hash' values from ledger.jsonl (latest first if limit is set)."""
    if not LEDGER_PATH.exists():
        return []
    hashes: List[str] = []
    with LEDGER_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                h = rec.get("rolling_hash")
                if h and isinstance(h, str):
                    hashes.append(h)
            except json.JSONDecodeError:
                continue
    if limit:
        return hashes[-limit:]
    return hashes


# ---------------- Merkle utilities ----------------

def merkle_root(entries: List[str]) -> str:
    """
    Compute a Merkle root from a list of hex-encoded hashes.
    - If the list is empty, returns "".
    - For odd counts per level, the last leaf is duplicated (classic approach).
    """
    if not entries:
        return ""
    level = [bytes.fromhex(h) for h in entries]
    while len(level) > 1:
        nxt: List[bytes] = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            nxt.append(hashlib.sha256(left + right).digest())
        level = nxt
    return level[0].hex()


def compute_root_from_ledger(limit: Optional[int] = None) -> Tuple[str, List[str]]:
    """
    Read the last `limit` rolling hashes from the ledger and compute the Merkle root.
    Returns (root, hashes_used).
    """
    hashes = _read_rolling_hashes_from_ledger(limit=limit)
    return merkle_root(hashes), hashes


# ---------------- Dispatcher ----------------

def anchor(root: str, provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Anchor `root` externally using the given provider. Returns a provider-specific receipt
    with the Sovereign Identity Anchors attached. The provider can be set via:
      - argument `provider`
      - environment `BELEL_ANCHOR_PROVIDER` (default: "ipfs")
    """
    if not root or not isinstance(root, str) or len(root) < 8:
        raise ValueError("Invalid Merkle root.")

    provider = (provider or os.getenv("BELEL_ANCHOR_PROVIDER", "ipfs")).lower().strip()
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

    # Attach identity anchors & meta
    receipt["sovereign_anchors"] = SOVEREIGN_ANCHORS
    receipt["root"] = root
    receipt["provider"] = provider
    receipt["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return receipt


# ---------------- Providers (optional, lazy) ----------------

def _anchor_ipfs(root: str, **kw) -> Dict[str, Any]:
    """
    Pin a small JSON doc to IPFS via HTTP API.
    Requires IPFS_API env, e.g. http://127.0.0.1:5001/api/v0
    """
    import requests  # local import to avoid hard dependency when unused

    api = os.getenv("IPFS_API")
    if not api:
        raise RuntimeError("Missing IPFS_API (e.g. http://127.0.0.1:5001/api/v0)")

    doc = {
        "type": "belel.merkle.anchor",
        "root": root,
        "meta": kw.get("meta", {}),
        "anchors": SOVEREIGN_ANCHORS,
        "ts": time.time(),
    }
    files = {"file": ("anchor.json", json.dumps(doc), "application/json")}
    r = requests.post(f"{api.rstrip('/')}/add", files=files, timeout=30)
    r.raise_for_status()
    res = r.json()
    cid = res.get("Hash") or res.get("Cid") or res.get("hash")
    return {"cid": cid, "api": api, "note": "Pinned anchor.json with Merkle root"}


def _anchor_bitcoin(root: str, **kw) -> Dict[str, Any]:
    """
    Anchor via Bitcoin OP_RETURN using the `bit` library (https://ofek.dev/bit/).
    - Testnet by default. Set BITCOIN_NET=mainnet to use mainnet.
    - Requires BITCOIN_WIF (private key in WIF format with UTXOs).
    Optional:
      BITCOIN_FEE_SATS (default 600), will create a data output only (OP_RETURN).
    """
    try:
        from bit import Key, PrivateKeyTestnet
        from bit.network import NetworkAPI
    except Exception as e:
        raise RuntimeError("Bitcoin provider requires `bit`. Install: pip install bit") from e

    net = os.getenv("BITCOIN_NET", "testnet").lower()
    wif = os.getenv("BITCOIN_WIF")
    if not wif:
        raise RuntimeError("Missing BITCOIN_WIF (private key WIF). Use testnet for safety.")

    KeyClass = PrivateKeyTestnet if net != "mainnet" else Key
    key = KeyClass(wif)

    op_return_msg = f"belel:merkle:{root}".encode("utf-8")
    fee = int(os.getenv("BITCOIN_FEE_SATS", "600"))

    # Create & broadcast OP_RETURN tx
    try:
        tx_hex = key.create_transaction(
            outputs=[(key.address, 0, "data", op_return_msg)],
            fee=fee,
            absolute_fee=True,
        )
        NetworkAPI.broadcast_tx(tx_hex)
    except Exception as e:
        raise RuntimeError(f"Bitcoin broadcast failed: {e}") from e

    return {
        "network": net,
        "from": key.address,
        "tx_hex": tx_hex,
        "note": "Broadcasted OP_RETURN with Merkle root",
    }


def _anchor_tezos(root: str, **kw) -> Dict[str, Any]:
    """
    Anchor on Tezos by writing the root via `pytezos`.
    ENV:
      TEZOS_NODE   = https://rpc.tzkt.io/ghostnet   (example testnet)
      TEZOS_SECRET = <edsk... private key>
      TEZOS_CONTRACT (optional): if set, implement a specific entrypoint call.
    """
    try:
        from pytezos import pytezos
    except Exception as e:
        raise RuntimeError("Tezos provider requires `pytezos`. Install: pip install pytezos") from e

    node = os.getenv("TEZOS_NODE")
    secret = os.getenv("TEZOS_SECRET")
    if not node or not secret:
        raise RuntimeError("Missing TEZOS_NODE or TEZOS_SECRET")

    p = pytezos.using(key=secret, shell=node)
    contract_addr = os.getenv("TEZOS_CONTRACT")

    if contract_addr:
        # TODO: Replace with your specific contract call, e.g. `p.contract(addr).record(root).autofill().sign().inject()`
        raise NotImplementedError("Implement your Tezos contract entrypoint call here.")
    else:
        # Demo: zero-amount self tx (for a visible op hash). Use a contract in production.
        op = (
            p.transaction(destination=p.key.public_key_hash(), amount=0)
            .autofill()
            .sign()
            .inject(_async=False)
        )
        return {
            "node": node,
            "account": p.key.public_key_hash(),
            "op_hash": op.get("hash"),
            "note": "Demo: injected zero-amount tx. For production, call a contract to store the root.",
        }


def _anchor_arweave(root: str, **kw) -> Dict[str, Any]:
    """
    Upload via Bundlr HTTP API (illustrative).
    ENV:
      BUNDLR_NODE     = https://node1.bundlr.network
      BUNDLR_CURRENCY = arweave | matic | etc.
      BUNDLR_SECRET   = <private key / wallet secret> (use official SDKs for signing in production)
    """
    import requests  # local import to avoid hard dependency

    node = os.getenv("BUNDLR_NODE")
    currency = os.getenv("BUNDLR_CURRENCY")
    secret = os.getenv("BUNDLR_SECRET")
    if not node or not currency or not secret:
        raise RuntimeError("Missing BUNDLR_NODE, BUNDLR_CURRENCY, or BUNDLR_SECRET")

    # Illustrative: most real integrations should use Bundlr SDK for signing & funding.
    doc = {
        "type": "belel.merkle.anchor",
        "root": root,
        "meta": kw.get("meta", {}),
        "anchors": SOVEREIGN_ANCHORS,
        "ts": time.time(),
    }
    r = requests.post(f"{node.rstrip('/')}/tx", json=doc, timeout=30)
    r.raise_for_status()
    res = r.json()
    return {
        "bundlr": node,
        "currency": currency,
        "tx_id": res.get("id") or res.get("txId"),
        "note": "Anchored via Bundlr (illustrative; prefer official SDK).",
    }


# ---------------- Batch helpers ----------------

def anchor_latest_batch(
    provider: Optional[str] = None,
    limit: Optional[int] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Convenience: compute a root from the last `limit` ledger entries and anchor it.
    If limit is None, anchors over all ledger entries (can be large).
    """
    root, hashes = compute_root_from_ledger(limit=limit)
    if not root:
        raise RuntimeError("No hashes found in ledger to anchor.")
    receipt = anchor(root, provider=provider, **kwargs)
    receipt["hash_count"] = len(hashes)
    return receipt


# ---------------- Verification ----------------

def verify_receipt(receipt: Dict[str, Any], limit: Optional[int] = None) -> bool:
    """
    Verify that the `receipt["root"]` is consistent with the current ledger.
    This checks only the Merkle relation; it does not verify chain inclusion on
    the external provider (that requires provider-specific queries).
    """
    if not isinstance(receipt, dict):
        return False
    root = receipt.get("root")
    if not root or not isinstance(root, str):
        return False
    recomputed, _ = compute_root_from_ledger(limit=limit)
    return recomputed == root
