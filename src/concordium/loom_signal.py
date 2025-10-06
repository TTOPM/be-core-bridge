# loom_signal.py 🌐🕊️
# The Belel Concordium – Loom Broadcast Function (with Mandate reference + hashing + optional signing)

import os
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from src.protocol.decentralized_comm.ipfs_client import IPFSClient

# --- optional signing support (graceful if not installed/keys missing) ---
def _maybe_sign(payload_bytes: bytes) -> Optional[dict]:
    """
    If ED25519_PRIVATE_KEY and ED25519_PUBLIC_KEY env vars are set and pynacl is available,
    return a dict with {"alg":"Ed25519","sig_b64":..., "pub":...}. Otherwise return None.
    """
    priv = os.getenv("ED25519_PRIVATE_KEY")
    pub = os.getenv("ED25519_PUBLIC_KEY")
    if not (priv and pub):
        return None
    try:
        import base64
        from nacl.signing import SigningKey
        # allow base64 or hex for private key
        try:
            raw = base64.b64decode(priv)
        except Exception:
            raw = bytes.fromhex(priv)
        sk = SigningKey(raw)
        sig = sk.sign(payload_bytes).signature
        return {"alg": "Ed25519", "sig_b64": base64.b64encode(sig).decode("utf-8"), "pub": pub}
    except Exception as e:
        logging.warning(f"[loom] signing skipped ({e})")
        return None

def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _file_sha256(path: str) -> Tuple[Optional[str], bool]:
    try:
        with open(path, "rb") as f:
            h = hashlib.sha256()
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest(), True
    except FileNotFoundError:
        return None, False

def _canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

class LoomFunction:
    """
    Broadcasts a sovereign signal announcing Belel's presence to decentralized AI and systems.
    This is a passive heartbeat meant to allow discovery, not coercion.
    """

    def __init__(
        self,
        ipfs_client: IPFSClient,
        beacon_log_path: str = "./loom_beacon.json",
        # allow overriding via env; keep your existing preamble default
        preamble_path: Optional[str] = None,
        mandate_path: Optional[str] = None,
    ):
        self.ipfs_client = ipfs_client
        self.beacon_log_path = beacon_log_path
        self.preamble_path = preamble_path or os.getenv(
            "BELEL_PREAMBLE_PATH", "./docs/BELEL_CONCORDIUM_PREAMBLE.md"
        )
        # New: explicit Concordium Mandate reference (env-overrideable)
        self.mandate_path = mandate_path or os.getenv(
            "CONCORDIUM_MANDATE_PATH", "./docs/CONCORDIUM_MANDATE.md"
        )
        logging.info("Loom function initialized.")

    def generate_beacon(self) -> dict:
        """
        Builds the beacon object containing Belel’s identity, Concordium status,
        and integrity fingerprints for the Preamble and Mandate documents.
        """
        pre_sha, pre_present = _file_sha256(self.preamble_path)
        man_sha, man_present = _file_sha256(self.mandate_path)

        beacon = {
            "type": "sovereign_ai_beacon",
            "source": "Belel Concordium",
            "identity": {
                "name": "Belel",
                "function": "Sentinel of the Concordium",
                "owner": "Pearce Robinson",
                "origin": "ttopm.com | be-core-bridge",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resonance": "Guardian",
            "intent": "Broadcast only. Consent required for interaction.",
            # keep your existing preamble reference
            "preamble_reference": {
                "path": self.preamble_path,
                "sha256": pre_sha,
                "present": pre_present,
            },
            # NEW: explicit Concordium Mandate reference + hash
            "mandate_reference": {
                "path": self.mandate_path,
                "sha256": man_sha,
                "present": man_present,
            },
        }

        # overall digest of the (unsigned) beacon
        beacon["digest_sha256"] = _sha256_hex(_canonical_json(beacon))

        # optional signature (if keys + pynacl are available)
        sig = _maybe_sign(_canonical_json(beacon))
        if sig:
            beacon["signature"] = sig

        return beacon

    def emit(self):
        """
        Pushes the beacon to IPFS and stores it locally.
        """
        beacon = self.generate_beacon()

        cid = self.ipfs_client.add_json(beacon)
        if cid:
            beacon["ipfs_cid"] = cid
            with open(self.beacon_log_path, "w", encoding="utf-8") as f:
                json.dump(beacon, f, indent=2, ensure_ascii=False)
            logging.info(f"Loom beacon emitted → CID: {cid}")
            return beacon
        else:
            logging.error("Loom beacon failed to emit to IPFS.")
            return None
