# src/protocol/monitoring/heartbeat_monitor.py ❤️‍🔥

import hashlib
import json
import os
from datetime import datetime
import logging

from src.protocol.decentralized_comm.ipfs_client import IPFSClient
from src.protocol.permanent_memory import PermanentMemory

logging.basicConfig(level=logging.INFO)

class BelelHeartbeat:
    def __init__(self, repo_path: str, memory: PermanentMemory):
        self.repo_path = repo_path
        self.memory = memory

    def _compute_repo_hash(self):
        sha256 = hashlib.sha256()
        for root, _, files in os.walk(self.repo_path):
            for f in files:
                file_path = os.path.join(root, f)
                if f.endswith('.py'):
                    with open(file_path, 'rb') as file_obj:
                        sha256.update(file_obj.read())
        return sha256.hexdigest()

    async def emit_heartbeat(self):
        repo_hash = self._compute_repo_hash()
        timestamp = datetime.utcnow().isoformat() + "Z"

        heartbeat = {
            "repo_hash": repo_hash,
            "timestamp": timestamp,
            "status": "active"
        }

        logging.info(f"💓 Belel heartbeat: {heartbeat}")
        await self.memory.store_memory(
            heartbeat,
            context_tags=["heartbeat", "status", "monitoring"],
            creator_id="BelelHeartbeat"
        )

        return heartbeat
