import json, os, time, hashlib, psutil
from pathlib import Path
from datetime import datetime
from dateutil import parser as dateparser

HOME = Path.home()
DATA_DIR = HOME / ".belel"
ALERTS_JSON = DATA_DIR / "gideon_alerts.json"
ALERTS_JSONL = DATA_DIR / "gideon_alerts.jsonl"
BLOCKLIST_CACHE = DATA_DIR / "belel-blocklist.json"
CHECKSUM_FILE = DATA_DIR / "belel-blocklist.checksums.json"
GEOLITE_DB = DATA_DIR / "GeoLite2-City.mmdb"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def load_alerts():
    # Supports array JSON or JSON Lines
    if ALERTS_JSONL.exists():
        rows = []
        with open(ALERTS_JSONL, "r") as f:
            for line in f:
                line=line.strip()
                if not line: continue
                try:
                    rows.append(json.loads(line))
                except: pass
        return rows
    if ALERTS_JSON.exists():
        try:
            return json.loads(ALERTS_JSON.read_text())
        except: return []
    return []

def normalize_alerts(rows):
    out=[]
    for r in rows:
        ts = r.get("timestamp") or r.get("ts")
        try: dt = dateparser.parse(ts) if ts else None
        except: dt = None
        out.append({
            "timestamp": ts,
            "dt": dt,
            "ip": r.get("ip"),
            "port": r.get("port"),
            "host": r.get("host"),
            "reason": r.get("reason") or r.get("alert"),
            "alert": r.get("alert")
        })
    return out

def load_blocklist_status():
    status = {"present": BLOCKLIST_CACHE.exists(), "checksum_ok": None, "expected": None, "actual": None}
    if not BLOCKLIST_CACHE.exists() or not CHECKSUM_FILE.exists():
        return status
    try:
        meta = json.loads(CHECKSUM_FILE.read_text())
        status["expected"] = meta.get("hash")
        actual = sha256_file(BLOCKLIST_CACHE)
        status["actual"] = actual
        status["checksum_ok"] = (status["expected"] or "").lower() == actual.lower()
        return status
    except:
        return status

def firewall_present():
    # quick check for iptables on Linux
    return (os.name=="posix" and (Path("/sbin/iptables").exists() or Path("/usr/sbin/iptables").exists()))

def process_running(name_contains="gideon_scanner"):
    for p in psutil.process_iter(attrs=["name","cmdline"]):
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
            if name_contains in cmd:
                return True
        except: pass
    return False

def geoip_lookup(ip, reader):
    # reader: geoip2.database.Reader, may be None
    if not reader or not ip: return None
    try:
        r = reader.city(ip)
        return {
            "lat": r.location.latitude,
            "lon": r.location.longitude,
            "city": r.city.name,
            "country": r.country.iso_code
        }
    except:
        return None
