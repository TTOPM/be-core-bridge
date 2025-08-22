# src/protocol/security/violation_scanner.py 🔍🧠

import os
import hashlib
import json
from datetime import datetime
from src.protocol.permanent_memory import PermanentMemory
from src.protocol.decentralized_comm.ipfs_client import IPFSClient

class ViolationScanner:
    """
    Scans for and logs violations of file integrity, particularly related to Symbiont operations.
    """
    def __init__(self, monitored_files, memory_path="./memory_store.json", baseline_path="./hash_baseline.json"):
        self.monitored_files = monitored_files
        self.memory = PermanentMemory(memory_path)
        self.baseline_path = baseline_path
        self.ipfs = IPFSClient()
        self.baseline = self._load_baseline()

    def _load_baseline(self):
        if os.path.exists(self.baseline_path):
            with open(self.baseline_path, "r") as f:
                return json.load(f)
        else:
            return self._generate_baseline()

    def _generate_baseline(self):
        baseline = {}
        for file_path in self.monitored_files:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                baseline[file_path] = file_hash
        with open(self.baseline_path, "w") as f:
            json.dump(baseline, f, indent=4)
        return baseline

    def scan_for_violations(self, agent_id="Unknown"):
        for file_path in self.monitored_files:
            if not os.path.exists(file_path):
                self._log_violation(file_path, "FILE_MISSING", agent_id)
                continue

            with open(file_path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()

            baseline_hash = self.baseline.get(file_path)
            if not baseline_hash:
                self._log_violation(file_path, "NO_BASELINE_FOUND", agent_id)
                continue

            if current_hash != baseline_hash:
                self._log_violation(file_path, "HASH_MISMATCH", agent_id)
                self.memory.log_symbiont_breach(
                    file_path=file_path,
                    breach_type="HASH_MISMATCH",
                    agent_id=agent_id
                )

    def _log_violation(self, file_path, breach_type, agent_id="Unknown"):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": breach_type,
            "file": file_path,
            "agent": agent_id,
            "symbiont_event": True,
            "source_script": "violation_scanner.py"
        }
        self.memory.write("violation", event)

        # Store hash in IPFS for tamper-proof history
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                ipfs_hash = self.ipfs.store(f.read())
            event["ipfs_cid"] = ipfs_hash
            self.memory.write("violation_ipfs", event)

        print(f"[Symbiont Alert] {breach_type} in {file_path} by agent {agent_id}")
