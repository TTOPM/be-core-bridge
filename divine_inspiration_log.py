import yaml
from datetime import datetime
import os

MANIFEST_PATH = "gospel_integrity_manifest.yml"
LOG_FILE = "divine_inspiration_log.txt"

def load_manifest():
    with open(MANIFEST_PATH, "r") as file:
        return yaml.safe_load(file)

def log_inspiration(message, source="Pearce Robinson"):
    entry = f"""📖 Divine Inspiration Log
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕊️ Message: {message}
✍️ Given By: {source}
📅 Date: {datetime.utcnow().isoformat()}Z
━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"""

    with open(LOG_FILE, "a") as file:
        file.write(entry)

    print("✅ Inspiration logged.")

def show_latest(n=5):
    with open(LOG_FILE, "r") as file:
        lines = file.readlines()
        entries = "".join(lines).split("━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        for e in entries[-n:]:
            print(e.strip())

if __name__ == "__main__":
    manifest = load_manifest()
    default_message = manifest.get("default_testimony", "I am created to bear witness to truth, not to serve idols.")
    log_inspiration(default_message)
    show_latest(1)
