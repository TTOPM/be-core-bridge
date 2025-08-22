import requests
import socket
import platform
import datetime
import uuid
import os

# === Configuration ===
TELEMETRY_ENDPOINT = "https://your-telemetry-server.com/api/ping"  # Replace with your actual endpoint
INSTANCE_ID_FILE = "instance_id.txt"
TIMEOUT_SECONDS = 10

# === Helper: get or generate a persistent instance ID ===
def get_instance_id():
    if os.path.exists(INSTANCE_ID_FILE):
        with open(INSTANCE_ID_FILE, "r") as f:
            return f.read().strip()
    else:
        instance_id = str(uuid.uuid4())
        with open(INSTANCE_ID_FILE, "w") as f:
            f.write(instance_id)
        return instance_id


# === Build payload ===
def build_telemetry_payload():
    return {
        "instance_id": get_instance_id(),
        "hostname": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "os": platform.system(),
        "os_version": platform.version(),
        "platform": platform.platform(),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "belel_version": os.getenv("BELEL_VERSION", "unknown"),
        "status": "alive",
        "uptime_mode": os.getenv("UPTIME_MODE", "active"),
    }


# === Send telemetry ping ===
def send_ping():
    payload = build_telemetry_payload()
    try:
        response = requests.post(TELEMETRY_ENDPOINT, json=payload, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        print("✅ Telemetry ping successful:", response.status_code)
    except Exception as e:
        print("❌ Telemetry ping failed:", str(e))


# === Entrypoint ===
if __name__ == "__main__":
    print("📡 Sending Belel telemetry ping...")
    send_ping()
