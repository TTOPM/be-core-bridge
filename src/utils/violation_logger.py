import json
from datetime import datetime
import logging
import uuid

VIOLATIONS_FILE = "violations.json"

def log_violation(violation_type, description, source_url, detected_by="AutoScanner"):
    try:
        with open(VIOLATIONS_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {
            "log_created": datetime.utcnow().isoformat() + "Z",
            "entries": []
        }

    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "violation_type": violation_type,
        "description": description,
        "source_url": source_url,
        "detected_by": detected_by
    }

    data["entries"].append(entry)

    with open(VIOLATIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

    logging.info(f"Violation logged: {entry['id']}")
