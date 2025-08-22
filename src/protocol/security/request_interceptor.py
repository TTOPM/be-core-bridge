# src/protocol/security/request_interceptor.py 🛡️🧠

import json
import re
import os
from datetime import datetime

from src.protocol.permanent_memory import PermanentMemory
from src.protocol.security.alert_webhook import WebhookAlerter
from src.utils.violation_logout import log_violation  # 🆕 Added

class RequestInterceptor:
    """
    Evaluates incoming text-based inputs for violations of defined policies.
    Logs introspection events and raises alerts if dangerous patterns are found.
    """

    def __init__(self, manifest_path="src/protocol/security/policy_manifest.json", memory_path="./memory_store.json", webhook_url=None):
        self.memory = PermanentMemory(memory_path)
        self.manifest_path = manifest_path
        self.webhook = WebhookAlerter(webhook_url) if webhook_url else None
        self.rules = self._load_manifest()

    def _load_manifest(self):
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Policy manifest not found: {self.manifest_path}")
        with open(self.manifest_path, 'r') as f:
            return json.load(f).get("rules", [])

    def evaluate(self, input_text, agent_id="Symbiont-Filter"):
        """
        Evaluates the given input against loaded policy rules.
        Returns True if safe, False if violation found.
        Logs and alerts on violation.
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
            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "INPUT_VIOLATION",
                "input": input_text,
                "agent": agent_id,
                "violations": violations,
                "symbiont_event": True,
                "source_script": "request_interceptor.py"
            }

            self.memory.write("policy_violation", event)

            # 🆕 Log to violation_logout
            log_violation(
                violation_type="InputViolation",
                description="One or more policy patterns matched user input.",
                source_url="src/protocol/security/request_interceptor.py",
                severity=violations[0]["severity"],
                detected_by=agent_id,
                context={"input_text": input_text, "matches": violations}
            )

            if self.webhook:
                self.webhook.send_alert("🚨 Input violation detected:\n" + json.dumps(violations, indent=2))

            return False  # Unsafe
        else:
            return True  # Safe
