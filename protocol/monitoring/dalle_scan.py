# src/protocol/monitoring/dalle_scan.py 🧠🎨

import logging
import json
from datetime import datetime
from src.core.memory.permanent_memory import PermanentMemory
from src.utils.dalle_wrapper import generate_dalle_insights
from src.protocol.decentralized_comm.ipfs_client import IPFSClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DalleViolationScanner:
    def __init__(self, memory_system: PermanentMemory, ipfs_client: IPFSClient):
        self.memory = memory_system
        self.ipfs = ipfs_client

    async def scan_image(self, image_path: str, source_domain: str = "unknown"):
        """
        Sends an image for visual analysis and stores the result if any violations are detected.
        """
        insights = generate_dalle_insights(image_path)
        timestamp = datetime.utcnow().isoformat() + "Z"

        result = {
            "timestamp": timestamp,
            "image_path": image_path,
            "source_domain": source_domain,
            "dalle_interpretation": insights
        }

        # Store interpretation as violation entry
        cid = self.ipfs.add_json(result)
        await self.memory.store_memory(
            data=result,
            context_tags=["violation", "visual", "DALL·E"],
            creator_id="DalleViolationScanner"
        )

        logging.info(f"DALL·E scan completed and stored for {image_path}")
        return cid
