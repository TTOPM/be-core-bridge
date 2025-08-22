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
        self.ipfs = IPFSClient()

    def _load_or_init_baseline(self):
        if os.path.exists(self.hashlog_path):
            with open(self.hashlog_path, "r") as f:
                return json.load(f)
        else:
            baseline = {}
            for file_path in self.monitored_files:
                baseline[file_path] = self._calculate_hash(file_path)
            with open(self.hashlog_path, "w") as f:
                json.dump(baseline, f, indent=4)
            return baseline

    def _calculate_hash(self, file_path):
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                buf = f.read()
                hasher.update(buf)
            return hasher.hexdigest()
        except FileNotFoundError:
            logging.warning(f"File not found for hashing: {file_path}")
            return None

    def _check_file_integrity(self, file_path):
        current_hash = self._calculate_hash(file_path)
        expected_hash = self.hash_baseline.get(file_path)
        if current_hash != expected_hash:
            logging.warning(f"Integrity check failed for {file_path}")
            self.log_symbiont_breach(file_path, breach_type="HASH_MISMATCH")
            return False
        return True

    def run_integrity_checks(self):
        logging.info("Running sovereignty integrity checks...")
        for file_path in self.monitored_files:
            self._check_file_integrity(file_path)

    def update_baseline(self):
        logging.info("Updating baseline hash record...")
        for file_path in self.monitored_files:
            self.hash_baseline[file_path] = self._calculate_hash(file_path)
        with open(self.hashlog_path, "w") as f:
            json.dump(self.hash_baseline, f, indent=4)

    def log_symbiont_breach(self, file_path, breach_type="UNAUTHORIZED_MODIFICATION", agent_id="Unknown"):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": breach_type,
            "file": file_path,
            "agent": agent_id,
            "symbiont_event": True,
            "source_script": "sovereignty_guard.py"
        }
        try:
            ipfs_hash = self.ipfs.add_json(event)
            event["ipfs_hash"] = ipfs_hash
        except Exception as e:
            logging.warning(f"IPFS logging failed: {e}")
        self.memory.write("symbiont_violation", event)
