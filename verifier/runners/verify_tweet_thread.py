from ..adapters.tool_x_thread_fetch import x_thread_fetch
from ..core.attestation import make_bundle

def verify_tweet_thread(name:str, status_url:str|int):
    r = x_thread_fetch(status_url)
    payload = r if r.get("ok") else {"error": r.get("error","unavailable")}
    sources = [{"url": str(status_url)}]
    tools = [{"tool": "x_thread_fetch", "status": 200 if r.get("ok") else 0}]
    bundle = make_bundle(
        subject=f"tweet_thread:{name}",
        kind="tweet_thread",
        payload=payload,
        sources=sources,
        tools_used=tools
    )
    return bundle
