# src/protocol/security/request_interceptor.py 🛡️🧠

import json
import re
import os
import hashlib
from datetime import datetime

from src.protocol.permanent_memory import PermanentMemory
from src.protocol.security.alert_webhook import WebhookAlerter
from src.utils.violation_logout import log_violation

class RequestInterceptor:
    """
    Evaluates incoming text-based inputs for violations of defined policies.
    Logs introspection events, triggers alerts, and fingerprints offenders.
    """

    def __init__(self, manifest_path="src/protocol/security/policy_manifest.json",
                 memory_path="./memory_store.json", webhook_url=None):
        self.memory = PermanentMemory(memory_path)
        self.manifest_path = manifest_path
        self.webhook = WebhookAlerter(webhook_url) if webhook_url else None
        self.rules = self._load_manifest()

    def _load_manifest(self):
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Policy manifest not found: {self.manifest_path}")
        with open(self.manifest_path, 'r') as f:
            return json.load(f).get("rules", [])

    def generate_fingerprint(self, user_id: str, ip_address: str, user_agent: str) -> str:
        """
        Generates a SHA256 fingerprint to pseudonymously track input sources.
        """
        base = f"{user_id}-{ip_address}-{user_agent}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def evaluate(self, input_text, agent_id="Symbiont-Filter",
                 user_id=None, ip_address=None, user_agent=None):
        """
        Evaluates input text against policy rules. Logs, alerts, and invokes response logic on violation.
        Returns True if input is safe, False otherwise.
        """
        violations = []

        for rule in self.rules:
            pattern = rule.get("pattern")
            description = rule.get("description", "No description")
            severity = rule.get("severity", "low")

            if re.search(pattern, input_text, re.IGNORECASE):
                violations.append({
                    "pattern": pattern,
                    "description": description,
                    "severity": severity
                })

        if violations:
            fingerprint = self.generate_fingerprint(user_id or "anon", ip_address or "0.0.0.0", user_agent or "unknown")

            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "INPUT_VIOLATION",
                "input": input_text,
                "agent": agent_id,
                "violations": violations,
                "symbiont_event": True,
                "source_script": "request_interceptor.py",
                "fingerprint": fingerprint
            }

            self.memory.write("policy_violation", event)

            if self.webhook:
                self.webhook.send_alert("🚨 Input violation detected:\n" + json.dumps(violations, indent=2))

            # Call out to centralized violation handler
            log_violation(
                event_type="INPUT_VIOLATION",
                severity=violations[0]["severity"],  # Use first match severity
                metadata=event
            )

            return False  # Input is unsafe
        else:
            return True  # Input is safe
