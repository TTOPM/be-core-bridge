# src/protocol/monitoring/violation_scanner.py 🔎🛡️

import os
import json
import logging
from datetime import datetime
from src.utils.whois_lookup import perform_whois_lookup
from src.utils.dns_lookup import perform_dns_lookup
from src.core.memory.permanent_memory import PermanentMemory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ViolationScanner:
    def __init__(self, memory_system: PermanentMemory, violations_log_path: str = "./violations.json"):
        self.memory = memory_system
        self.violations_log_path = violations_log_path
        self.violations_log = self._load_or_init_log()

    def _load_or_init_log(self):
        if os.path.exists(self.violations_log_path):
            with open(self.violations_log_path, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    logging.warning("Corrupted violations log. Reinitializing.")
                    return {}
        else:
            return {}

    def _store_log(self):
        with open(self.violations_log_path, "w") as f:
            json.dump(self.violations_log, f, indent=2)

    async def scan_domain(self, domain: str, evidence: str = None):
        timestamp = datetime.utcnow().isoformat() + "Z"
        whois_info = perform_whois_lookup(domain)
        dns_info = perform_dns_lookup(domain)

        violation_id = f"{domain}-{timestamp}"
        entry = {
            "violation_id": violation_id,
            "detected_at": timestamp,
            "domain": domain,
            "evidence": evidence or "n/a",
            "whois": whois_info,
            "dns": dns_info
        }

        # Store to local log
        self.violations_log[violation_id] = entry
        self._store_log()

        # Store to decentralized permanent memory
        await self.memory.store_memory(
            data=entry,
            context_tags=["violation", "scanner", "domain"],
            creator_id="ViolationScanner"
        )

        logging.info(f"Violation logged for {domain}")

        return entry
