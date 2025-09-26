#!/usr/bin/env python3
import yaml, requests, json
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "blocklists" / "dynamic_feeds.yaml"
OUT = REPO_ROOT / "blocklists" / "merged-blocklist.json"
CACHE = Path.home() / ".belel" / "merged-blocklist.json"
CACHE.parent.mkdir(parents=True, exist_ok=True)

def parse_text_to_ranges(text):
    out=[]; 
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith("#"):
            continue
        out.append([line, line])
    return out

def merge_feeds():
    cfg = yaml.safe_load(CONFIG.read_text())
    final = {"ip_ranges": [], "domains": [], "source": "merged", "last_updated": None}
    for feed in cfg["feeds"]:
        try:
            r = requests.get(feed["url"], timeout=10)
            if feed.get("format") == "text":
                final["ip_ranges"].extend(parse_text_to_ranges(r.text))
            elif feed.get("format") == "json":
                j = r.json()
                final["ip_ranges"].extend(j.get("ip_ranges", []))
                final["domains"].extend(j.get("domains", []))
        except Exception as e:
            print("feed error", feed["name"], e)
    final["last_updated"] = __import__("datetime").datetime.utcnow().isoformat()+"Z"
    OUT.write_text(json.dumps(final, indent=2))
    CACHE.write_text(json.dumps(final, indent=2))
    print("Merged feeds written to", OUT, "and cache")

if __name__ == "__main__":
    merge_feeds()
