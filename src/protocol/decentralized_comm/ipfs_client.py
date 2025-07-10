# src/protocol/decentralized_comm/ipfs_client.py 🌐🗃️

import json
import ipfshttpclient
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class IPFSClient:
    """
    Interface to IPFS for storing and retrieving JSON data.
    """
    def __init__(self, ipfs_address: str = "/dns/localhost/tcp/5001/http"):
        self.client = ipfshttpclient.connect(ipfs_address)
        logging.info(f"Connected to IPFS node at {ipfs_address}")

    def add_json(self, data: dict) -> str:
        try:
            encoded = json.dumps(data).encode("utf-8")
            result = self.client.add_bytes(encoded)
            logging.info(f"Data added to IPFS: CID {result}")
            return result
        except Exception as e:
            logging.error(f"IPFS add_json failed: {e}")
            return None

    def cat_json(self, cid: str) -> dict:
        try:
            data = self.client.cat(cid).decode("utf-8")
            decoded = json.loads(data)
            logging.info(f"Data retrieved from IPFS: CID {cid}")
            return decoded
        except Exception as e:
            logging.error(f"IPFS cat_json failed for CID {cid}: {e}")
            return None
