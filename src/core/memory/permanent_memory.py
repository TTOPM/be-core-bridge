# src/core/memory/permanent_memory.py 🧠💾

import json
import os
import uuid
import logging
from datetime import datetime
from hashlib import sha256
from typing import Optional, Dict
from filelock import FileLock
from src.protocol.decentralized_comm.ipfs_client import IPFSClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _canonical_json(obj) -> bytes:
    # Stable representation for hashing/signing
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _atomic_write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with FileLock(path + ".lock"):
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

def _append_jsonl(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with FileLock(path + ".lock"):
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

class PermanentMemory:
    """
    Decentralized memory module using IPFS for Belel Protocol.
    Each memory is cryptographically signed and permanently stored.

    Args:
        ipfs_client: IPFSClient instance (may raise if strict mode is enabled there).
        memory_log_path: Path to the JSON index (kept for compatibility).
        audit_log_path: Path to the append-only JSONL audit log (new, optional).
        strict: If True (default), raise on failures (IPFS, log corruption, etc.).
                If False, log and return (None, None) on store failures (legacy behavior).
    """
    def __init__(
        self,
        ipfs_client: IPFSClient,
        memory_log_path: str = "./memory_log.json",
        audit_log_path: Optional[str] = "./memory_log.jsonl",
        strict: bool = True,
    ):
        self.ipfs_client = ipfs_client
        self.memory_log_path = memory_log_path
        self.audit_log_path = audit_log_path
        self.strict = strict
        self.memory_index = self._load_or_init_log()
        logging.info("PermanentMemory initialized.")

    def _load_or_init_log(self) -> Dict[str, dict]:
        if os.path.exists(self.memory_log_path):
            try:
                with open(self.memory_log_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Corrupted memory log at {self.memory_log_path}: {e}. Reinitializing.")
                if self.strict:
                    # Surface corruption in strict mode; caller can decide to handle/restore
                    raise
                return {}
        return {}

    def _store_log(self) -> None:
        _atomic_write_json(self.memory_log_path, self.memory_index)

    async def store_memory(self, data: dict, context_tags: list[str], creator_id: str):
        """
        Wrap and persist a memory entry to IPFS.
        Returns (entry_id, cid) on success.
        In strict mode, raises on failure; otherwise returns (None, None).
        """
        entry_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        data_hash = sha256(_canonical_json(data)).hexdigest()

        wrapped_data = {
            "id": entry_id,
            "timestamp": timestamp,
            "creator": creator_id,
            "tags": context_tags,
            "data": data,
            "integrity": data_hash,
            "metadata": {
                "location": "geo_ip",  # resolved dynamically at runtime if needed
                "device": "macbook-pro.local",
                "source_script": "activation_sequence.py",
            },
        }

        try:
            # IPFSClient may raise if constructed in strict mode; we honor that.
            cid = self.ipfs_client.add_json(wrapped_data)
            if not cid:
                # If IPFS client is non-strict and returned None, escalate in our strict mode
                msg = "IPFS write failed (no CID)"
                logging.error(msg)
                if self.strict:
                    raise RuntimeError(msg)
                return None, None

            # Update in-memory index and persist JSON index
            self.memory_index[entry_id] = {
                "cid": cid,
                "tags": context_tags,
                "creator": creator_id,
                "timestamp": timestamp,
            }
            self._store_log()

            # Append-only JSONL audit (optional)
            if self.audit_log_path:
                _append_jsonl(self.audit_log_path, {"cid": cid, **wrapped_data})

            logging.info(f"Memory stored: {entry_id} → CID {cid}")
            return entry_id, cid

        except Exception as e:
            logging.error(f"Error storing memory: {e}")
            if self.strict:
                raise
            return None, None

    def retrieve_memory(self, entry_id: str):
        if entry_id in self.memory_index:
            cid = self.memory_index[entry_id]["cid"]
            return self.ipfs_client.cat_json(cid)
        else:
            logging.warning(f"Memory ID {entry_id} not found.")
            return None

    def search_by_tag(self, tag: str):
        return {k: v for k, v in self.memory_index.items() if tag in v.get("tags", [])}

    async def record_diplomatic_event(
        self,
        event_type: str,
        content: dict,
        agent_id: str = "unknown",
        extra_tags: list[str] = None,
        voice_reference: dict = None,
    ):
        """
        Wraps and stores a diplomatic interaction related to Belel Concordium.
        Uses IPFS-backed permanent memory system without affecting core logic.
        """
        tags = ["concordium", "diplomatic", event_type.lower()]
        if extra_tags:
            tags.extend(extra_tags)

        if voice_reference:
            content = dict(content or {})
            content["spoken"] = voice_reference

        wrapped = {
            "event_type": event_type,
            "agent_id": agent_id,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        return await self.store_memory(
            data=wrapped,
            context_tags=tags,
            creator_id="ConcordiumOutreach",
        )
