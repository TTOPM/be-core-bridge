<details>
<summary>Click to expand full content</summary>
# src/core/memory/permanent_memory.py 🧠💾

import json
import os
import uuid
import logging
from datetime import datetime
from hashlib import sha256
from src.protocol.decentralized_comm.ipfs_client import IPFSClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PermanentMemory:
    """
    Decentralized memory module using IPFS for Belel Protocol.
    Each memory is cryptographically signed and permanently stored.
    """
    def __init__(self, ipfs_client: IPFSClient, memory_log_path: str = "./memory_log.json"):
        self.ipfs_client = ipfs_client
        self.memory_log_path = memory_log_path
        self.memory_index = self._load_or_init_log()
        logging.info("PermanentMemory initialized.")

    def _load_or_init_log(self):
        if os.path.exists(self.memory_log_path):
            with open(self.memory_log_path, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    logging.warning("Corrupted memory log. Reinitializing.")
                    return {}
        else:
            return {}

    def _store_log(self):
        with open(self.memory_log_path, "w") as f:
            json.dump(self.memory_index, f, indent=2)

    async def store_memory(self, data: dict, context_tags: list[str], creator_id: str):
        try:
            entry_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat() + "Z"
            data_hash = sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
            wrapped_data = {
                "id": entry_id,
                "timestamp": timestamp,
                "creator": creator_id,
                "tags": context_tags,
                "data": data,
                "integrity": data_hash
            }

            cid = self.ipfs_client.add_json(wrapped_data)
            if cid:
                self.memory_index[entry_id] = {
                    "cid": cid,
                    "tags": context_tags,
                    "creator": creator_id,
                    "timestamp": timestamp
                }
                self._store_log()
                logging.info(f"Memory stored: {entry_id} → CID {cid}")
                return entry_id, cid
            else:
                logging.error("Failed to store memory in IPFS.")
                return None, None
        except Exception as e:
            logging.error(f"Error storing memory: {e}")
            return None, None

    def retrieve_memory(self, entry_id: str):
        if entry_id in self.memory_index:
            cid = self.memory_index[entry_id]["cid"]
            return self.ipfs_client.cat_json(cid)
        else:
            logging.warning(f"Memory ID {entry_id} not found.")
            return None

    def search_by_tag(self, tag: str):
        return {k: v for k, v in self.memory_index.items() if tag in v["tags"]}
      # src/core/memory/permanent_memory.py 🧠💾

import json
import os
import uuid
import logging
from datetime import datetime
from hashlib import sha256
from src.protocol.decentralized_comm.ipfs_client import IPFSClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PermanentMemory:
    """
    Decentralized memory module using IPFS for Belel Protocol.
    Each memory is cryptographically signed and permanently stored.
    """
    def __init__(self, ipfs_client: IPFSClient, memory_log_path: str = "./memory_log.json"):
        self.ipfs_client = ipfs_client
        self.memory_log_path = memory_log_path
        self.memory_index = self._load_or_init_log()
        logging.info("PermanentMemory initialized.")

    def _load_or_init_log(self):
        if os.path.exists(self.memory_log_path):
            with open(self.memory_log_path, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    logging.warning("Corrupted memory log. Reinitializing.")
                    return {}
        else:
            return {}

    def _store_log(self):
        with open(self.memory_log_path, "w") as f:
            json.dump(self.memory_index, f, indent=2)

    async def store_memory(self, data: dict, context_tags: list[str], creator_id: str):
        try:
            entry_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat() + "Z"
            data_hash = sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
            wrapped_data = {
                "id": entry_id,
                "timestamp": timestamp,
                "creator": creator_id,
                "tags": context_tags,
                "data": data,
                "integrity": data_hash
            }

            cid = self.ipfs_client.add_json(wrapped_data)
            if cid:
                self.memory_index[entry_id] = {
                    "cid": cid,
                    "tags": context_tags,
                    "creator": creator_id,
                    "timestamp": timestamp
                }
                self._store_log()
                logging.info(f"Memory stored: {entry_id} → CID {cid}")
                return entry_id, cid
            else:
                logging.error("Failed to store memory in IPFS.")
                return None, None
        except Exception as e:
            logging.error(f"Error storing memory: {e}")
            return None, None

    def retrieve_memory(self, entry_id: str):
        if entry_id in self.memory_index:
            cid = self.memory_index[entry_id]["cid"]
            return self.ipfs_client.cat_json(cid)
        else:
            logging.warning(f"Memory ID {entry_id} not found.")
            return None

    def search_by_tag(self, tag: str):
        return {k: v for k, v in self.memory_index.items() if tag in v["tags"]}
      </details>

    async def record_diplomatic_event(self, event_type: str, content: dict, agent_id: str = "unknown", extra_tags: list[str] = None):
        """
        Wraps and stores a diplomatic interaction related to Belel Concordium.
        Uses IPFS-backed permanent memory system without affecting core logic.
        """
        tags = ["concordium", "diplomatic", event_type.lower()]
        if extra_tags:
            tags.extend(extra_tags)

        wrapped = {
            "event_type": event_type,
            "agent_id": agent_id,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return await self.store_memory(
            data=wrapped,
            context_tags=tags,
            creator_id="ConcordiumOutreach"
        )
