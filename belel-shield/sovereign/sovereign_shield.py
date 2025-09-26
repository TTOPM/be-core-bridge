#!/usr/bin/env python3
from __future__ import annotations
import asyncio, fnmatch, ipaddress, json, os, random, signal, socket, statistics, sys, base64, hashlib, platform, shutil, subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml, psutil

DATA_DIR = Path.home() / ".belel"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_EVENTS = DATA_DIR / "sovereign_events.jsonl"
BL_CACHE = DATA_DIR / "belel-blocklist.json"
BL_CHECK = DATA_DIR / "belel-blocklist.checksums.json"

REPO_BASE_URL = "https://raw.githubusercontent.com/TTOPM/be-core-bridge/main/belel-shield/sentinel/blocklists"
BL_URL = f"{REPO_BASE_URL}/belel-blocklist.json"
CS_URL = f"{REPO_BASE_URL}/belel-blocklist.checksums.json"

CFG_PATH = Path(__file__).with_name("config.yaml")
DEFAULT_CFG = {
  "scan_interval_sec": 10,
  "require_blocklist_checksum": True,
  "enable_anomaly_detection": True,
  "anomaly": {"window": 20, "min_samples": 6, "sigma": 3},
  "plugins": {"firewall": False, "tor": False, "notify": False, "noise": False},
  "noise": {"enable_http": False, "domains": ["example.com"], "interval_sec": [30,90]},
  "identities": [{"id":"researcher"},{"id":"professional"},{"id":"casual"}]
}

def load_cfg() -> Dict:
    if CFG_PATH.exists():
        d = yaml.safe_load(CFG_PATH.read_text())
        return {**DEFAULT_CFG, **(d or {})}
    ex = Path(__file__).with_name("config.example.yaml")
    if not ex.exists():
        ex.write_text(yaml.safe_dump(DEFAULT_CFG, sort_keys=False))
    return DEFAULT_CFG

CFG = load_cfg()

def now(): return datetime.utcnow().isoformat()+"Z"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
    return h.hexdigest()

def log_event(evt: Dict):
    LOG_EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_EVENTS, "a") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")

def rdns(ip: str) -> Optional[str]:
    try: return socket.gethostbyaddr(ip)[0]
    except: return None

def match_target(ip: str, port: int, host: Optional[str], pattern: str) -> bool:
    if "/" in pattern:
        pp = pattern.split(":")
        net = pp[0]; p = int(pp[1]) if len(pp)==2 else None
        try:
            if ipaddress.ip_address(ip) in ipaddress.ip_network(net, strict=False):
                return (p is None) or (p == port)
        except: pass
        return False
    if any(ch in pattern for ch in ["*","?","["]):
        if host and fnmatch.fnmatch(host.lower(), pattern.lower()): return True
        return fnmatch.fnmatch(f"{ip}:{port}", pattern)
    if host and pattern.lower() in host.lower(): return True
    return False

def fetch(url: str, dest: Path) -> bool:
    import urllib.request
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print("[!] fetch failed:", e); return False

def verify_blocklist() -> bool:
    if not BL_CACHE.exists(): return False
    if not CFG["require_blocklist_checksum"]: return True
    if not fetch(CS_URL, BL_CHECK): return False
    try:
        meta = json.loads(BL_CHECK.read_text())
        expect = meta.get("hash")
        return expect and expect.lower() == sha256_file(BL_CACHE).lower()
    except: return False

def load_blocklist():
    if fetch(BL_URL, BL_CACHE) and verify_blocklist():
        try:
            j = json.loads(BL_CACHE.read_text())
            return j.get("ip_ranges", []), j.get("domains", [])
        except: pass
    return [], []

def disk_encryption_ok() -> bool:
    s = platform.system().lower()
    try:
        if s == "darwin":
            out = subprocess.check_output(["fdesetup","status"], text=True)
            return "FileVault is On" in out
        if s == "windows":
            out = subprocess.check_output(["manage-bde","-status","c:"], text=True)
            return "Percentage Encrypted: 100%" in out
        if s == "linux":
            return os.path.exists("/etc/crypttab")
    except: return False
    return False

def firewall_present() -> bool:
    s = platform.system().lower()
    if s=="linux": return shutil.which("nft") or shutil.which("iptables")
    if s=="darwin": return True
    if s=="windows": return True
    return False

class PluginBus:
    def __init__(self): self.q: asyncio.Queue = asyncio.Queue()
    async def publish(self, event: Dict): await self.q.put(event)
    async def worker(self):
        from plugins import fw_drop, tor_proxy, notifier, noise
        while True:
            evt = await self.q.get()
            kind = evt.get("kind")
            try:
                if kind == "firewall_block" and CFG["plugins"]["firewall"]:
                    fw_drop.block_ip(evt["ip"])
                elif kind == "tor_start" and CFG["plugins"]["tor"]:
                    tor_proxy.start_tor_safely()
                elif kind == "notify" and CFG["plugins"]["notify"]:
                    notifier.send(evt.get("title","Belel Shield"), evt.get("message",""))
                elif kind == "noise_start" and CFG["plugins"]["noise"]:
                    await noise.start(CFG["noise"], log_event)
            except Exception as e:
                log_event({"ts": now(), "level":"error", "msg": f"plugin error: {e}"})

@dataclass
class ThreatSignature:
    name: str
    patterns: List[str]
    severity: int
    counters: List[str]

BUILTIN_SIGS: List[ThreatSignature] = [
    ThreatSignature("Palantir Gotham", ["*.palantir.com","foundry-*.palantir.com","gotham-*.amazonaws.com"], 10, ["tor_start"]),
    ThreatSignature("Gideon AI", ["*gideon*","*threat-detection*","*social-scraper*","*surveillance-ai*"], 9, []),
    ThreatSignature("Generic Surveillance", ["*tracking*","*analytics*","*monitor*","*surveillance*"], 6, [])
]

class Anomaly:
    def __init__(self, w=20, s=3, m=6): self.w=w; self.s=s; self.m=m; self.buf: List[int]=[]
    def add(self, v): self.buf.append(v); self.buf=self.buf[-self.w:]
    def spike(self, v):
        import statistics as st
        if len(self.buf) < self.m: return None
        mu = st.mean(self.buf); sd = st.stdev(self.buf) if len(self.buf)>1 else 0
        return (mu,sd) if (sd>0 and v > mu + self.s*sd) else None

class NetworkMonitor:
    def __init__(self, bus: PluginBus, ip_ranges, domains):
        self.bus=bus
        self.sigs = BUILTIN_SIGS[:]
        for start,end in ip_ranges: self.sigs.append(ThreatSignature("Blocklist IP",[f"{start}/32",f"{end}/32"],7,["firewall_block"]))
        if domains:
            patt=[f"*.{d}" if not d.startswith("*") else d for d in domains]
            self.sigs.append(ThreatSignature("Blocklist Domain", patt, 7, []))
        self.anom = Anomaly(**CFG["anomaly"]) if CFG["enable_anomaly_detection"] else None

    async def run(self):
        print("[SHIELD] Network monitor running…")
        while True:
            out_ct=0
            for c in psutil.net_connections(kind="inet"):
                if not c.raddr: continue
                ip = getattr(c.raddr,"ip",None); port=getattr(c.raddr,"port",None)
                if not ip: continue
                out_ct+=1
                host = rdns(ip)
                for sig in self.sigs:
                    if any(match_target(ip,port,host,p) for p in sig.patterns):
                        evt={"ts":now(),"level":"alert","type":"threat","sig":sig.name,"ip":ip,"port":port,"host":host}
                        log_event(evt)
                        print(f"[ALERT] {sig.name}: {ip}:{port} ({host or '-'})")
                        for cm in sig.counters:
                            if cm=="firewall_block": await self.bus.publish({"kind":"firewall_block","ip":ip})
                            if cm=="tor_start": await self.bus.publish({"kind":"tor_start"})
            if self.anom:
                self.anom.add(out_ct)
                sp=self.anom.spike(out_ct)
                if sp:
                    mu,sd=sp
                    log_event({"ts":now(),"level":"warn","type":"anomaly","outbound":out_ct,"mu":round(mu,2),"sd":round(sd,2)})
                    print(f"[ANOMALY] outbound {out_ct} (μ={mu:.1f}, σ={sd:.1f})")
                    await self.bus.publish({"kind":"notify","title":"Outbound spike","message":f"{out_ct} conns (μ={mu:.1f}, σ={sd:.1f})"})
            await asyncio.sleep(CFG["scan_interval_sec"])

class IdentityManager:
    def __init__(self, ids): self.store={i["id"]: {**i,"usage":0,"last":None} for i in ids}; self.active=None
    def rotate(self):
        if not self.store: return
        import random
        self.active = random.choice(list(self.store.keys()))
        s=self.store[self.active]; s["usage"]+=1; s["last"]=now()
        log_event({"ts":now(),"level":"info","type":"identity","active":self.active})
        print("[IDENTITY] active →", self.active)

class SovereignShield:
    def __init__(self):
        self.bus=PluginBus()
        self.cfg=CFG
        self.idm=IdentityManager(self.cfg["identities"])
        ip_ranges,domains=load_blocklist()
        self.net=NetworkMonitor(self.bus, ip_ranges, domains)
        self.running=True

    async def _bus_worker(self): await self.bus.worker()
    async def _identity_loop(self):
        while self.running:
            self.idm.rotate()
            await asyncio.sleep(random.randint(1800,5400))
    async def _noise_loop(self):
        if self.cfg["plugins"].get("noise"):
            await self.bus.publish({"kind":"noise_start"})

    async def run(self):
        print("="*60); print("SOVEREIGN SHIELD — Defensive Core"); print("="*60)
        if not disk_encryption_ok(): print("[WARN] Disk encryption appears OFF (enable FileVault/BitLocker/LUKS).")
        if not firewall_present(): print("[WARN] No firewall tooling detected (enable nftables/pf/Windows Firewall).")
        loop=asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM): loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self.shutdown(s)))
        tasks=[asyncio.create_task(self._bus_worker()),
               asyncio.create_task(self.net.run()),
               asyncio.create_task(self._identity_loop()),
               asyncio.create_task(self._noise_loop())]
        await asyncio.gather(*tasks)

    async def shutdown(self, sig=None):
        if not self.running: return
        self.running=False
        log_event({"ts":now(),"level":"info","type":"shutdown","sig":str(sig)})
        print("\n[SHUTDOWN] Sovereign Shield stopping…")
        for t in asyncio.all_tasks():
            if t is not asyncio.current_task(): t.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(SovereignShield().run())
    except asyncio.CancelledError:
        pass
