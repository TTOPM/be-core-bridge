# src/protocol/decentralized_comm/ipfs_client.py 🌐🗃️

import os
import json
import logging
import ipfshttpclient
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class IPFSClient:
    """
    Interface to IPFS for storing and retrieving JSON data.

    Args:
        ipfs_address: Multiaddr for the IPFS API. Falls back to IPFS_API_ADDR env
                      or '/dns/localhost/tcp/5001/http'.
        strict: If True, raise RuntimeError on failures. If False, return None on failures.
        pin_on_add: If True, pin CIDs after adding (best-effort).
    """
    def __init__(
        self,
        ipfs_address: Optional[str] = None,
        *,
        strict: bool = True,
        pin_on_add: bool = False,
    ):
        addr = ipfs_address or os.getenv("IPFS_API_ADDR", "/dns/localhost/tcp/5001/http")
        self.strict = strict
        self.pin_on_add = pin_on_add

        try:
            self.client = ipfshttpclient.connect(addr)
            # Lightweight check that we can actually talk to the node
            _ = self.client.id()
            logging.info(f"Connected to IPFS node at {addr}")
        except Exception as e:
            logging.error(f"Failed to connect to IPFS at {addr}: {e}")
            if self.strict:
                raise RuntimeError(f"IPFS connect failed: {e}") from e
            self.client = None

    def _fail(self, msg: str, exc: Exception | None = None):
        logging.error(msg)
        if self.strict:
            raise RuntimeError(msg) from exc
        return None

    def add_json(self, data: dict) -> Optional[str]:
        """
        Add a JSON object to IPFS. Returns the CID string on success.
        """
        if not self.client:
            return self._fail("IPFS add_json failed: no active client", None)

        try:
            encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            cid = self.client.add_bytes(encoded)
            if self.pin_on_add:
                try:
                    self.client.pin.add(cid)
                except Exception as e:
                    logging.warning(f"Pinning CID {cid} failed (continuing): {e}")
            logging.info(f"Data added to IPFS: CID {cid}")
            return cid
        except Exception as e:
            return self._fail(f"IPFS add_json failed: {e}", e)

    def cat_json(self, cid: str) -> Optional[dict]:
        """
        Retrieve and decode a JSON object from IPFS by CID.
        """
        if not self.client:
            return self._fail("IPFS cat_json failed: no active client", None)

        try:
            raw = self.client.cat(cid)
            decoded = json.loads(raw.decode("utf-8"))
            logging.info(f"Data retrieved from IPFS: CID {cid}")
            return decoded
        except Exception as e:
            return self._fail(f"IPFS cat_json failed for CID {cid}: {e}", e)

            logging.info(f"Data retrieved from IPFS: CID {cid}")
            return decoded
        except Exception as e:
            logging.error(f"IPFS cat_json failed for CID {cid}: {e}")
            return None
