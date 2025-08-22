import json
import uuid
import logging
from datetime import datetime
from pathlib import Path

# Optional integrations
try:
    from src.protocol.security.alert_webhook import WebhookAlerter
    from src.protocol.permanent_memory import PermanentMemory
    memory = PermanentMemory()
except ImportError:
    WebhookAlerter = None
    memory = None

# === CONFIG ===
VIOLATIONS_JSON = Path("violations.json")
VIOLATIONS_STREAM = Path("violations.jsonl")  # JSON Lines format
ENABLE_DISCORD_ALERTS = True
WEBHOOK_URL = "https://discord.com/api/webhooks/xxx/yyy"  # Replace with your real one

# === LOGGER SETUP ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_violation(
    violation_type,
    description,
    source_url=None,
    severity="medium",
    detected_by="AutoScanner",
    context=None
):
    """
    Logs a violation to both JSON and streaming JSONL files.
    Optionally triggers alerts and writes to permanent memory.
    """
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "violation_type": violation_type,
        "description": description,
        "source_url": source_url,
        "severity": severity,
        "detected_by": detected_by,
        "context": context or {}
    }

    # === Write to violations.json ===
    try:
        if VIOLATIONS_JSON.exists():
            with open(VIOLATIONS_JSON, "r") as f:
                data = json.load(f)
        else:
            data = {"log_created": datetime.utcnow().isoformat() + "Z", "entries": []}
    except Exception:
        data = {"log_created": datetime.utcnow().isoformat() + "Z", "entries": []}

    data["entries"].append(entry)
    with open(VIOLATIONS_JSON, "w") as f:
        json.dump(data, f, indent=2)

    # === Write to violations.jsonl ===
    with open(VIOLATIONS_STREAM, "a") as f:
        f.write(json.dumps(entry) + "\n")

    logging.warning(f"[{severity.upper()}] Violation logged: {violation_type} – {description}")

    # === Alert Webhook ===
    if ENABLE_DISCORD_ALERTS and WebhookAlerter:
        try:
            alerter = WebhookAlerter(WEBHOOK_URL)
            alerter.send_alert(f"🚨 Violation Detected: `{violation_type}`\n> {description}")
        except Exception as e:
            logging.error(f"Failed to send webhook alert: {e}")

    # === Permanent Memory Sync ===
    if memory:
        memory.write("violation_log", entry)

    return entry
