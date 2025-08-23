#!/usr/bin/env python3

import os
import socket
import datetime

def get_ip_info():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return hostname, local_ip

def log_clone_attempt():
    timestamp = datetime.datetime.now().isoformat()
    hostname, ip = get_ip_info()

    log_entry = f"""--- CLONE WATCH ---
Timestamp: {timestamp}
Hostname: {hostname}
IP Address: {ip}
Environment: {os.environ.get('USER', 'unknown')}
Shell: {os.environ.get('SHELL', 'unknown')}
-------------------
"""

    log_path = "clone-monitor/WITNESS_LOGS/clone_activity.log"
    with open(log_path, "a") as log_file:
        log_file.write(log_entry)
        print("[🛡] Clone Sentinel triggered. Activity logged.")

if __name__ == "__main__":
    log_clone_attempt()
