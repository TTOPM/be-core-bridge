
import time
from typing import Dict
_rate = {"web.search":0, "calendar.search":0, "code.generate":0, "echo":0}
def _ratelimit(name, per=0.2):
    now=time.time()
    if now - _rate.get(name,0) < per:
        raise RuntimeError(f"ratelimited:{name}")
    _rate[name]=now
def run_tool(name:str, args:Dict)->str:
    _ratelimit(name)
    if name == "echo":
        return args.get("text","")
    if name == "web.search":
        q=args.get("q",""); return f"search-results for '{q}' (placeholder)"
    if name == "calendar.search":
        q=args.get("q",""); return f"calendar-matches for '{q}' (placeholder)"
    if name == "code.generate":
        p=args.get("prompt",""); return f"code stub for: {p[:80]}..."
    return "tool:unknown"
