#!/usr/bin/env python3
"""
gideon_scanner.py
Belel Protocol – Citizen Counter-Surveillance Module (Next-Gen)

Monitors active connections for Gideon/Palantir-like surveillance patterns.
- Blocklist + SHA-256 verification (safe updates from repo/IPFS mirrors)
- Outbound anomaly detection (3-sigma spike rule)
- Optional local firewall DROP (Linux iptables only)
- Optional desktop notifications (plyer)

Safe by design: logs locally; never exfiltrates data.
"""

import datetime
import hashlib
import json
import os
import platform
import socket
import statistics
import subprocess
import time
import urllib.request
from pathlib import Path

import psutil  # pip install psutil

# =========================
# CONFIG (tweak as needed)
# =========================
SCAN_INTERVAL = 10  # seconds between scans
ENABLE_ANOMALY_DETECTION = True
ANOMALY_WINDOW = 20       # samples kept
ANOMALY_MIN_SAMPLES = 6   # need this many before checking spikes
ANOMALY_SIGMA = 3         # 3-sigma rule

# Remote blocklist + checksum (point to your repo/mirror raw URLs)
BASE_URL = "https://raw.githubusercontent.com/TTOPM/be-core-bridge/main/belel-shield/sentinel/blocklists"
BLOCKLIST_URL = f"{BASE_URL}/belel-blocklist.json"
CHECKSUM_URL  = f"{BASE_URL}/belel-blocklist.checksums.json"

AUTO_FETCH_BLOCKLIST_ON_START = True
REQUIRE_CHECKSUM_MATCH = True

# Local actions
AUTO_FIREWALL = False  # set True to auto-DROP flagged IPs (Linux iptables only)
DESKTOP_NOTIFICATIONS = False  # set True if you want pop-up notifications (requires 'plyer')

# =========================
# FILES / STATE
# =========================
DATA_DIR = Path.home() / ".belel"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA_DIR / "gideon_alerts.json"
BLOCKLIST_CACHE = DATA_DIR / "belel-blocklist.json"
CHECK_FILE = DATA_DIR / "belel-blocklist.checksums.json"

# Built-in starter fingerprints (extended by verified blocklist)
SUSPECT_IP_RANGES = [
    ("104.244.42.0", "104.244.42.255"),   # example
    ("185.220.100.0", "185.220.100.255"), # example
]
SUSPECT_DOMAINS = [
    "gideon-surveillance.com",
    "israel-trade-detect.net",
    "nsa-mirror.org",
]

_outbound_history = []  # for anomaly detection

# =========================
# UTILITIES
# =========================
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"

def notify(title: str, message: str):
    if not DESKTOP_NOTIFICATIONS:
        return
    try:
        from plyer import notification  # pip install plyer
        notification.notify(title=title, message=message, timeout=5)
    except Exception:
        # Best-effort; remain silent if plyer or desktop env absent
        pass

def log_event(event: dict):
    existing = []
    if LOG_FILE.exists():
        try:
            existing = json.loads(LOG_FILE.read_text())
        except Exception:
            existing = []
    existing.append(event)
    LOG_FILE.write_text(json.dumps(existing, indent=2))

def ip_in_range(ip: str, start: str, end: str) -> bool:
    import ipaddress
    ip_obj = ipaddress.ip_address(ip)
    return ipaddress.ip_address(start) <= ip_obj <= ipaddress.ip_address(end)

def fetch(url: str, dest: Path) -> bool:
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print(f"[!] Fetch failed: {url} -> {e}")
        return False

def verify_cached_blocklist() -> bool:
    """Download checksum metadata and verify cached blocklist hash."""
    if not REQUIRE_CHECKSUM_MATCH:
        return BLOCKLIST_CACHE.exists()
    ok_meta = fetch(CHECKSUM_URL, CHECK_FILE)
    if not ok_meta:
        print("[!] Could not fetch checksum metadata.")
        return False
    try:
        meta = json.loads(CHECK_FILE.read_text())
        if meta.get("algo") != "sha256" or "hash" not in meta:
            print("[!] Invalid checksum file; refusing cache.")
            return False
        if not BLOCKLIST_CACHE.exists():
            print("[i] No cached blocklist present.")
            return False
        local_hash = sha256_file(BLOCKLIST_CACHE)
        if local_hash.lower() != meta["hash"].lower():
            print("[!] Cached blocklist hash mismatch; ignoring cache.")
            return False
        return True
    except Exception as e:
        print(f"[!] Checksum verification error: {e}")
        return False

def try_update_blocklist():
    """Fetch latest blocklist JSON into cache (verification checked separately)."""
    ok = fetch(BLOCKLIST_URL, BLOCKLIST_CACHE)
    if ok:
        print("[+] Downloaded blocklist to cache.")
    return ok

def load_blocklist_into_memory():
    try:
        data = json.loads(BLOCKLIST_CACHE.read_text())
        ips = data.get("ip_ranges", [])
        doms = data.get("domains", [])
        added_ip = 0
        for rng in ips:
            if isinstance(rng, (list, tuple)) and len(rng) == 2:
                SUSPECT_IP_RANGES.append((rng[0], rng[1]))
                added_ip += 1
        for d in doms:
            if isinstance(d, str):
                SUSPECT_DOMAINS.append(d)
        print(f"[+] Activated +{added_ip} IP ranges, +{len(doms)} domains from verified blocklist.")
    except Exception as e:
        print(f"[!] Failed loading blocklist cache: {e}")

def apply_firewall_block(ip: str):
    """Local firewall DROP rule (Linux iptables). No-op on other OS or failure."""
    if not AUTO_FIREWALL:
        return
    if platform.system().lower() != "linux":
        return
    try:
        # add OUTPUT rule if not present
        subprocess.run(["sudo", "iptables", "-C", "OUTPUT", "-d", ip, "-j", "DROP"],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "iptables", "-A", "OUTPUT", "-d", ip, "-j", "DROP"], check=False)
        # add INPUT rule if not present
        subprocess.run(["sudo", "iptables", "-C", "INPUT", "-s", ip, "-j", "DROP"],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"], check=False)
        print(f"[FIREWALL] DROP {ip}")
    except Exception as e:
        print(f"[!] Firewall rule failed for {ip}: {e}")

# =========================
# CORE SCANNING
# =========================
def scan_connections():
    """Scan active connections and flag suspicious ones."""
    flagged = []
    outbound_count = 0

    for conn in psutil.net_connections(kind="inet"):
        if not conn.raddr:
            continue
        ip = getattr(conn.raddr, "ip", None)
        port = getattr(conn.raddr, "port", None)
        if not ip:
            continue
        outbound_count += 1

        try:
            host = socket.gethostbyaddr(ip)[0]
        except Exception:
            host = None

        # IP range check
        suspicious_ip = False
        for start, end in SUSPECT_IP_RANGES:
            try:
                if ip_in_range(ip, start, end):
                    flagged.append((ip, port, host, "range"))
                    suspicious_ip = True
                    break
            except Exception:
                pass

        # Domain check
        if (not suspicious_ip) and host and any(d in host for d in SUSPECT_DOMAINS):
            flagged.append((ip, port, host, "domain"))

    return flagged, outbound_count

def anomaly_detection(current_outbound: int):
    """Simple rolling 3-sigma detection of outbound connection spikes."""
    if not ENABLE_ANOMALY_DETECTION:
        return False, None, None

    _outbound_history.append(current_outbound)
    if len(_outbound_history) > ANOMALY_WINDOW:
        _outbound_history.pop(0)

    if len(_outbound_history) >= ANOMALY_MIN_SAMPLES:
        mean = statistics.mean(_outbound_history)
        stdev = statistics.stdev(_outbound_history) if len(_outbound_history) > 1 else 0
        if stdev > 0 and current_outbound > mean + ANOMALY_SIGMA * stdev:
            return True, mean, stdev

    return False, None, None

# =========================
# MAIN
# =========================
def main():
    print("🛡️ Belel Gideon Scanner (Next-Gen) running… (Ctrl+C to stop)")

    # Optional: fetch & verify blocklist at start
    if AUTO_FETCH_BLOCKLIST_ON_START:
        if try_update_blocklist() and verify_cached_blocklist():
            load_blocklist_into_memory()
        else:
            print("[!] Using built-in fingerprints only (no verified blocklist).")

    print(f"[i] Watching every {SCAN_INTERVAL}s | Firewall={'ON' if AUTO_FIREWALL else 'OFF'} | Notifications={'ON' if DESKTOP_NOTIFICATIONS else 'OFF'}")

    while True:
        flagged, outbound_count = scan_connections()

        # Handle flagged connections
        for ip, port, host, reason in flagged:
            event = {
                "timestamp": now_iso(),
                "ip": ip, "port": port, "host": host,
                "reason": reason,
                "alert": "Potential Gideon-like surveillance detected"
            }
            print(f"[ALERT] {reason.upper()} → {ip}:{port} ({host})")
            log_event(event)
            notify("Belel Shield", f"Suspicious connection: {ip}:{port} ({host or 'unknown'})")
            apply_firewall_block(ip)

        # Anomaly detection
        anomaly, mean, stdev = anomaly_detection(outbound_count)
        if anomaly:
            msg = f"Outbound spike {outbound_count} (μ={mean:.1f}, σ={stdev:.1f})"
            event = {
                "timestamp": now_iso(),
                "outbound_count": outbound_count,
                "mean": round(mean, 2) if mean is not None else None,
                "stdev": round(stdev, 2) if stdev is not None else None,
                "alert": "Outbound traffic anomaly detected"
            }
            print(f"[ANOMALY] {msg}")
            log_event(event)
            notify("Belel Shield", msg)

        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[i] Stopped by user.")
