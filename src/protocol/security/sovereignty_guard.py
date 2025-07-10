# src/protocol/security/sovereignty_guard.py 🛡️🧬

import os
import json
import hashlib
import logging
from datetime import datetime

from src.protocol.permanent_memory import PermanentMemory
from src.protocol.decentralized_comm.ipfs_client import IPFSClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SovereigntyGuard:
    """
    Guards the Belel Protocol against tampering, unauthorized forks, or violations of digital sovereignty.
    Logs and reports breaches into PermanentMemory.
    """
    def __init__(self, monitored_files: list, memory: PermanentMemory, hashlog_path: str = "./hash_baseline.json"):
        self.monitored_files = monitored_files
        self.memory = memory
        self.hashlog_path = hashlog_path
        self.hash_baseline = self._load_or_init_baseline()

    def _load_or_init_baseline(self):
        if os.path.exists(self.hashlog_path):
            with open(self.hashlog_path, "r") as f:
                return json.load(f)
        else:
            baseline = self._generate_current_hashes()
            with open(self.hashlog_path, "w") as f:
                json.dump(baseline, f, indent=2)
            return baseline

    def _generate_current_hashes(self):
        hashes = {}
        for file in self.monitored_files:
            if os.path.exists(file):
                with open(file, "rb") as f:
                    contents = f.read()
                    file_hash = hashlib.sha256(contents).hexdigest()
                    hashes[file] = file_hash
        return hashes

    async def scan_and_log(self):
        """
        Compares current file hashes with baseline. If mismatch, logs to PermanentMemory.
        """
        current = self._generate_current_hashes()
        violations = []
        for path, current_hash in current.items():
            if path not in self.hash_baseline or self.hash_baseline[path] != current_hash:
                violations.append({
                    "file": path,
                    "expected": self.hash_baseline.get(path),
                    "found": current_hash,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })

        if violations:
            logging.warning("Sovereignty violation(s) detected.")
            await self.memory.store_memory(
                {"violations": violations},
                context_tags=["tamper", "violation", "sovereignty"],
                creator_id="SovereigntyGuard"
            )
        else:
            logging.info("No violations detected. Integrity intact.")
