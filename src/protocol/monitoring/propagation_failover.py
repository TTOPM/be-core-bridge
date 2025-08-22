# src/protocol/monitoring/propagation_failover.py 🛰️

import logging
from datetime import datetime

from src.protocol.permanent_memory import PermanentMemory
from src.protocol.decentralized_comm.ipfs_client import IPFSClient

logging.basicConfig(level=logging.INFO)

class PropagationFailover:
    def __init__(self, memory: PermanentMemory, ipfs_client: IPFSClient, repo_path: str):
        self.memory = memory
        self.ipfs_client = ipfs_client
        self.repo_path = repo_path

    async def execute_failover(self):
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            res = self.ipfs_client.add_directory(self.repo_path)
            mirror_hash = res['Hash']

            logging.warning(f"🛑 Failover triggered. Repo mirrored to IPFS: {mirror_hash}")
            await self.memory.store_memory(
                {
                    "event": "failover_triggered",
                    "repo_mirror_hash": mirror_hash,
                    "timestamp": timestamp
                },
                context_tags=["failover", "propagation", "recovery"],
                creator_id="PropagationFailover"
            )

        except Exception as e:
            logging.error(f"❌ Failover failed: {str(e)}")
