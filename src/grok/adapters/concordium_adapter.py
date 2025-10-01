from __future__ import annotations
import os, json, hashlib, time

class ConcordiumAdapter:
    def __init__(self):
        self._cache_path = os.getenv("CONCORDIUM_CACHE", os.path.expanduser("~/.concordium/cache.json"))
        self._tip = None

    def reachable(self) -> bool:
        # ping logic or cached TTL
        return True

    def try_alt_gateways(self) -> None:
        pass  # rotate endpoints if you have multiple nodes

    def tip(self):
        # return latest mandate hash (sha256) if known
        if self._tip: return self._tip
        try:
            with open(self._cache_path,"r",encoding="utf-8") as f:
                data = json.load(f)
                self._tip = data.get("sha256")
                return self._tip
        except FileNotFoundError:
            return None

    def rebind(self, cid: str) -> None:
        # Rebind mandate to cid (update cache)
        payload = {"cid": cid, "loaded_ts": int(time.time()*1000)}
        payload["sha256"] = hashlib.sha256(cid.encode()).hexdigest()
        os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
        with open(self._cache_path,"w",encoding="utf-8") as f:
            json.dump(payload,f)
        self._tip = payload["sha256"]

from grok.grok_link_fetcher import LinkFetcher
# ...
text = LinkFetcher().fetch_text(f"https://your-gateway/{cid}").text
