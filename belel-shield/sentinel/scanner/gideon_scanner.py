#!/usr/bin/env python3
"""
gideon_scanner.py
Belel Protocol – Citizen Counter-Surveillance Module

This tool monitors network activity for signs of Gideon-like surveillance systems.
It detects suspicious connections, alerts the user, and logs events locally.
"""

import psutil
import socket
import time
import datetime
import json
from pathlib import Path

# Local log file (user-owned, never transmitted)
LOG_FILE = Path.home() / ".belel" / "gideon_alerts.json"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Example fingerprints (to be expanded via threat intel)
SUSPECT_IP_RANGES = [
    ("104.244.42.0", "104.244.42.255"),   # Example surveillance netblock
    ("185.220.100.0", "185.220.100.255"), # Example proxy network
]

SUSPECT_DOMAINS = [
    "gideon-surveillance.com",
    "israel-trade-detect.net",
    "nsa-mirror.org"
]

def ip_in_range(ip: str, start: str, end: str) -> bool:
    """Check if an IP is within a suspicious range."""
    import ipaddress
    ip_obj = ipaddress.ip_address(ip)
    return ipaddress.ip_address(start) <= ip_obj <= ipaddress.ip_address(end)

def log_event(event: dict):
    """Log surveillance detection locally."""
    if LOG_FILE.exists():
        existing = json.loads(LOG_FILE.read_text())
    else:
        existing = []

    existing.append(event)
    LOG_FILE.write_text(json.dumps(existing, indent=2))

def scan_connections():
    """Scan active connections and flag suspicious ones."""
    flagged = []
    for conn in psutil.net_connections(kind="inet"):
        if conn.raddr:
            ip, port = conn.raddr.ip, conn.raddr.port
            try:
                host = socket.gethostbyaddr(ip)[0]
            except Exception:
                host = None

            # Check suspicious IP ranges
            for start, end in SUSPECT_IP_RANGES:
                if ip_in_range(ip, start, end):
                    flagged.append((ip, port, host))

            # Check suspicious domain matches
            if host and any(domain in host for domain in SUSPECT_DOMAINS):
                flagged.append((ip, port, host))

    return flagged

def main():
    print("🛡️ Belel Gideon Scanner running... (Ctrl+C to stop)")
    while True:
        flagged = scan_connections()
        for ip, port, host in flagged:
            event = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "ip": ip,
                "port": port,
                "host": host,
                "alert": "Potential Gideon-like surveillance detected"
            }
            print(f"[ALERT] Suspicious connection → {ip}:{port} ({host})")
            log_event(event)
        time.sleep(10)  # scan every 10 seconds

if __name__ == "__main__":
    main()
