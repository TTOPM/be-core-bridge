# src/runtime/integrity_watchdog.py 🛡️⏱️

import os
import time
import json
from datetime import datetime, timedelta

from src.protocol.security.alert_webhook import WebhookAlerter
from src.protocol.permanent_memory import PermanentMemory
from src.runtime.guardian_runtime import GuardianRuntime

WEBHOOK_URL = "https://discord.com/api/webhooks/xxx/yyy"  # Replace with actual secure URL

class IntegrityWatchdog:
    """
    A continuous daemon that checks for anomalies in runtime behavior,
    introspection absence, or suspicious delays.
    """
    def __init__(self, memory_path="./memory_store.json", heartbeat_threshold_sec=180):
        self.memory = PermanentMemory(memory_path)
        self.alerter = WebhookAlerter(WEBHOOK_URL)
        self.heartbeat_threshold = timedelta(seconds=heartbeat_threshold_sec)
        self.guardian = GuardianRuntime(memory_path)

    def run(self):
        print("[🛡️] Watchdog active. Scanning for anomalies every 60s.")
        while True:
            self._check_last_heartbeat()
            self._check_manifest_consistency()
            time.sleep(60)  # Sleep between scans

    def _check_last_heartbeat(self):
        heartbeat = self.memory.read("introspection_status")
        if not heartbeat or "timestamp" not in heartbeat:
            self._trigger_alert("❌ Missing heartbeat record in memory.")
            return

        last_seen = datetime.fromisoformat(heartbeat["timestamp"])
        now = datetime.utcnow()

        if now - last_seen > self.heartbeat_threshold:
            self._trigger_alert(f"⚠️ No heartbeat from Symbiont Introspect for {now - last_seen}.")
        else:
            print(f"[✅] Heartbeat OK ({last_seen.isoformat()})")

    def _check_manifest_consistency(self):
        if not self.guardian.check_manifest_match(verbose=False):
            self._trigger_alert("🚨 Manifest mismatch detected by Integrity Watchdog.")

    def _trigger_alert(self, msg):
        print(f"[ALERT] {msg}")
        self.alerter.send_alert("🔐 INTEGRITY VIOLATION", msg)
        self._failsafe_protocol()

    def _failsafe_protocol(self):
        print("[🧨] Entering failsafe protocol.")
        # Insert any emergency shutdown or locking mechanism here.
        # e.g., os._exit(1), disable functionality, or isolate execution.
        self.memory.write("failsafe_triggered", {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": "Watchdog integrity violation"
        })
