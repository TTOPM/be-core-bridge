import time
import requests
from typing import Dict, Any, Optional

def _compute_backoff(attempt: int, retry_after: Optional[str]) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return min(30.0, 2 ** attempt)

def resilient_post(url: str, json: Dict[str, Any], headers: Dict[str, str], retries: int = 4) -> Dict[str, Any]:
    for attempt in range(retries):
        resp = requests.post(url, json=json, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 503):
            backoff = _compute_backoff(attempt, resp.headers.get("retry-after"))
            time.sleep(backoff)
            continue
        raise RuntimeError(f"xai_http_{resp.status_code}:{resp.text[:200]}")
    raise RuntimeError("xai_rate_limit_exceeded")
