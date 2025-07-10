<details>
<summary>Click to expand full PermanentMemory class</summary>
# src/core/memory/permanent_memory.py 🧠🗂️

import uuid
import logging
import json
from datetime import datetime

class PermanentMemory:
    """
    This class acts as Belel’s persistent memory core.
    All verifiable events, insights, and decisions are archived here.
    """
    def __init__(self):
        self.memory_store = {}  # Mock: replace with future DB or IPFS sync
        logging.info("PermanentMemory initialized.")

    async def store_memory(self, content: dict, context_tags=None, creator_id="belel-core"):
        """
        Stores a memory entry.
        Args:
            content (dict): The content to store.
            context_tags (list): Tags that describe the memory.
            creator_id (str): The ID of the entity storing the memory.
        Returns:
            tuple: (memory_id, cid) where cid is a conceptual content hash.
        """
        memory_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        record = {
            "id": memory_id,
            "timestamp": timestamp,
            "creator": creator_id,
            "tags": context_tags or [],
            "content": content
        }

        content_str = json.dumps(record, sort_keys=True)
        cid = f"cid_{uuid.uuid5(uuid.NAMESPACE_DNS, content_str).hex[:12]}"
        self.memory_store[memory_id] = {**record, "cid": cid}
        logging.debug(f"Memory stored with CID {cid}.")
        return memory_id, cid

    async def retrieve_memory(self, memory_id: str):
        """
        Retrieves memory by ID.
        """
        return self.memory_store.get(memory_id, None)

    async def query_by_tag(self, tag: str):
        """
        Searches all memory entries by tag.
        """
        return [v for v in self.memory_store.values() if tag in v["tags"]]
      </details>
