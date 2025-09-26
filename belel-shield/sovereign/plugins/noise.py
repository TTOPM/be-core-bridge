import asyncio, random
from datetime import datetime

def now(): return datetime.utcnow().isoformat()+"Z"

async def start(cfg, log):
    if not cfg.get("enable_http"):
        log({"ts": now(), "level":"info","type":"noise","msg":"disabled"})
        return
    lo, hi = cfg.get("interval_sec",[30,90])
    domains = cfg.get("domains",["example.com"])
    log({"ts": now(), "level":"info","type":"noise","msg":f"enabled {lo}-{hi}s"})
    while True:
        await asyncio.sleep(random.randint(lo,hi))
        dom = random.choice(domains)
        log({"ts": now(), "level":"info","type":"noise_event","domain": dom})
