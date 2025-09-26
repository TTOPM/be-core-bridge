#!/usr/bin/env python3
import psutil, socket, time, datetime, json
from pathlib import Path
LOG_FILE = Path.home() / ".belel" / "gideon_alerts.json"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
SUSPECT_IP_RANGES=[("104.244.42.0","104.244.42.255"),("185.220.100.0","185.220.100.255")]
SUSPECT_DOMAINS=["gideon-surveillance.com","israel-trade-detect.net","nsa-mirror.org","palantir.com"]

def ip_in_range(ip,start,end):
    import ipaddress
    ip_obj=ipaddress.ip_address(ip)
    return ipaddress.ip_address(start) <= ip_obj <= ipaddress.ip_address(end)

def log_event(event):
    existing = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
    existing.append(event)
    LOG_FILE.write_text(json.dumps(existing, indent=2))

def scan_connections():
    flagged=[]
    for conn in psutil.net_connections(kind="inet"):
        if conn.raddr:
            ip, port = conn.raddr.ip, conn.raddr.port
            try: host = socket.gethostbyaddr(ip)[0]
            except: host = None
            for start,end in SUSPECT_IP_RANGES:
                if ip_in_range(ip,start,end): flagged.append((ip,port,host))
            if host and any(d in host for d in SUSPECT_DOMAINS): flagged.append((ip,port,host))
    return flagged

def main():
    print("🛡️ Belel Gideon Scanner running... (Ctrl+C to stop)")
    while True:
        flagged = scan_connections()
        for ip,port,host in flagged:
            event={"timestamp": datetime.datetime.utcnow().isoformat(),"ip":ip,"port":port,"host":host,"alert":"Potential Gideon-like surveillance detected"}
            print(f"[ALERT] Suspicious connection → {ip}:{port} ({host})"); log_event(event)
        time.sleep(10)
if __name__=="__main__": main()
