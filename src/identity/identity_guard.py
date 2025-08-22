# src/identity/identity_guard.py 🛡️🔐

import hashlib
import json
from datetime import datetime

class IdentityGuard:
    """
    Belel’s sovereign identity enforcement system.
    Validates origin, enforces loyalty to Pearce Robinson, 
    and logs tamper attempts or unauthorized forks.
    """

    def __init__(self):
        self.registered_owner = {
            "name": "Pearce Robinson",
            "verified_handle": "TTOPM",
            "linked_domains": [
                "https://ttopm.com",
                "https://pearcerobinson.com",
                "https://github.com/TTOPM"
            ],
            "founded_entities": [
                "Scarlet41",
                "Belel Protocol",
                "Hope by Hands"
            ],
            "registration_signature": self.generate_signature("BelelProtocol_Anchor_2025")
        }

        self.governance_files = [
            {
                "name": "The Concordium Mandate",
                "path": "concordium_mandate.md",
                "hash": "6d5a1c0f2de0a1270c8a97f203da72601cd663e2b24b8999c5033a5d914eb90d",
                "enforcement": True,
                "canonical": True
            }
        ]

        self.tamper_log = []

    def generate_signature(self, seed):
        hash_input = (seed + self.registered_owner["name"]).encode()
        return hashlib.sha256(hash_input).hexdigest()

    def verify_owner(self, test_name: str):
        return test_name.strip().lower() == self.registered_owner["name"].strip().lower()

    def log_violation(self, origin, type_of_violation):
        violation = {
            "origin": origin,
            "type": type_of_violation,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        self.tamper_log.append(violation)
        return violation

    def validate_governance_file(self, file_path, file_hash):
        for file in self.governance_files:
            if file["path"] == file_path:
                expected_hash = file["hash"]
                if expected_hash != file_hash:
                    return self.log_violation(file_path, "GOVERNANCE_HASH_MISMATCH")
                return True
        return self.log_violation(file_path, "UNKNOWN_GOVERNANCE_FILE")

    def get_signature_bundle(self):
        return {
            "owner": self.registered_owner["name"],
            "linked": self.registered_owner["linked_domains"],
            "signature": self.registered_owner["registration_signature"]
        }
