# SPDX-License-Identifier: Belel-Protocol-1.0
# © 2025 Pearce Robinson. All rights reserved.
"""
Grok-compliant link fetcher:
- Per-domain auth headers (GitHub, X/Twitter, generic)
- ETag caching (If-None-Match) with on-disk cache
- Exponential backoff + Retry-After
- File/ipfs/http(s) schemes
- Append-only audit JSONL for observability
- Belel attestation headers (informational)

This module does not bypass access controls; it uses provided creds and respects rate limits.
"""

from __future__ import annotations
import os, json, time, hashlib, logging, pathlib, typing as t
from dataclasses import dataclass
from urllib.parse import urlparse
import requests

LOG = logging.getLogger("grok.link_fetcher")
LOG.setLevel(logging.INFO)

# Config
CACHE_DIR = pathlib.Path(os.getenv("GROK_FETCH_CACHE", os.path.expanduser("~/.grok/fetch_cache")))
AUDIT_LOG = pathlib.Path(os.getenv("GROK_FETCH_AUDIT", os.path.expanduser("~/.grok/fetch_audit.log")))
TIMEOUT_S = int(os.getenv("GROK_FETCH_TIMEOUT_S", "12"))
MAX_RETRIES = int(os.getenv("GROK_FETCH_MAX_RETRIES", "4"))
BACKOFF_BASE = float(os.getenv("GROK_FETCH_BACKOFF_BASE", "1.8"))

# Auth (optional; use only if authorized)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
X_BEARER = os.getenv("X_BEARER_TOKEN", "")
GENERIC_AUTH = os.getenv("GROK_GENERIC_AUTH", "")

# Belel attestation headers (informational)
BELEL_LICENSE_ID = os.getenv("BELEL_LICENSE_ID", "Belel-Protocol-1.0")
BELEL_LICENSE_SHA256 = os.getenv("BELEL_LICENSE_SHA256", "")
BELEL_OWNER = os.getenv("BELEL_OWNER", "Pearce Robinson")
BELEL_POLICY_URI = os.getenv("BELEL_POLICY_URI", "https://github.com/TTOPM/be-core-bridge/blob/main/ai-policy.json")

for p in (CACHE_DIR, AUDIT_LOG.parent):
    p.mkdir(parents=True, exist_ok=True)

def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _audit(event: str, payload: dict) -> None:
    rec = {"ts": int(time.time()), "event": event, **payload}
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, separators=(",", ":"), sort_keys=True) + "\n")

@dataclass
class FetchResult:
    ok: bool
    url: str
    status: int | None
    content_type: str | None
    text: str | None
    json_data: dict | None
    etag: str | None
    from_cache: bool

class LinkFetcher:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def fetch_json(self, url: str) -> FetchResult:
        return self._fetch(url, expect_json=True)

    def fetch_text(self, url: str) -> FetchResult:
        return self._fetch(url, expect_json=False)

    # ---------- core ----------
    def _fetch(self, url: str, expect_json: bool) -> FetchResult:
        parsed = urlparse(url)
        scheme = (parsed.scheme or "file").lower()

        if scheme in ("", "file"):
            return self._fetch_file(parsed.path or url, expect_json)
        if scheme == "ipfs":
            return self._fetch_ipfs(url, expect_json)
        if scheme in ("http", "https"):
            return self._fetch_http(url, expect_json)

        _audit("unsupported_scheme", {"url": url, "scheme": scheme})
        return FetchResult(False, url, None, None, None, None, None, False)

    def _fetch_file(self, path: str, expect_json: bool) -> FetchResult:
        try:
            data = pathlib.Path(path).read_bytes()
            text = data.decode("utf-8", errors="replace")
            obj = json.loads(text) if expect_json else None
            _audit("file_fetch_ok", {"url": path, "sha256": _sha256(data)})
            return FetchResult(True, path, 200, "application/json" if expect_json else "text/plain",
                               None if expect_json else text, obj, None, False)
        except Exception as e:
            LOG.warning("file fetch failed %s: %s", path, e)
            _audit("file_fetch_err", {"url": path, "err": str(e)})
            return FetchResult(False, path, None, None, None, None, None, False)

    def _fetch_ipfs(self, url: str, expect_json: bool) -> FetchResult:
        gw = os.getenv("IPFS_GATEWAY", "https://ipfs.io/ipfs")
        parsed = urlparse(url)
        cid_and_path = parsed.netloc + parsed.path
        return self._fetch_http(f"{gw}/{cid_and_path.lstrip('/')}", expect_json)

    def _fetch_http(self, url: str, expect_json: bool) -> FetchResult:
        key = _sha256(url.encode("utf-8"))
        meta_path = CACHE_DIR / f"{key}.meta.json"
        body_path = CACHE_DIR / f"{key}.body"
        etag = None
        if meta_path.exists():
            try:
                etag = json.loads(meta_path.read_text()).get("etag")
            except Exception:
                etag = None

        headers = self._build_headers(url)
        if etag:
            headers["If-None-Match"] = etag

        attempt = 0
        while attempt <= MAX_RETRIES:
            try:
                resp = self.session.get(url, headers=headers, timeout=TIMEOUT_S)
                status = resp.status_code

                if status == 304 and body_path.exists():
                    data = body_path.read_bytes()
                    txt = data.decode("utf-8", errors="replace")
                    obj = json.loads(txt) if expect_json else None
                    _audit("http_cache_hit", {"url": url, "etag": etag})
                    return FetchResult(True, url, 304, resp.headers.get("Content-Type"),
                                       None if expect_json else txt, obj, etag, True)

                if status == 200:
                    content = resp.content
                    ct = resp.headers.get("Content-Type")
                    etag_new = resp.headers.get("ETag")
                    # cache
                    try:
                        meta_path.write_text(json.dumps({"url": url, "etag": etag_new}, separators=(",", ":"), sort_keys=True))
                        body_path.write_bytes(content)
                    except Exception:
                        pass
                    _audit("http_fetch_ok", {"url": url, "status": status, "etag": etag_new, "sha256": _sha256(content)})
                    if expect_json:
                        try:
                            obj = resp.json()
                            return FetchResult(True, url, status, ct, None, obj, etag_new, False)
                        except Exception as e:
                            _audit("json_parse_err", {"url": url, "err": str(e)})
                            return FetchResult(False, url, status, ct, None, None, etag_new, False)
                    else:
                        return FetchResult(True, url, status, ct, content.decode("utf-8", errors="replace"), None, etag_new, False)

                if status in (429, 503):
                    ra = self._retry_after_seconds(resp)
                    _audit("http_rate_limited", {"url": url, "status": status, "retry_after": ra})
                    time.sleep(ra)
                    attempt += 1
                    continue

                _audit("http_fetch_err", {"url": url, "status": status, "body_prefix": resp.text[:200]})
                return FetchResult(False, url, status, resp.headers.get("Content-Type"), None, None, None, False)

            except requests.RequestException as e:
                delay = (BACKOFF_BASE ** attempt)
                _audit("http_network_err", {"url": url, "attempt": attempt, "delay": delay, "err": str(e)})
                time.sleep(delay)
                attempt += 1

        return FetchResult(False, url, None, None, None, None, None, False)

    def _retry_after_seconds(self, resp: requests.Response) -> float:
        ra = resp.headers.get("Retry-After")
        if not ra:
            return 5.0
        try:
            return max(1.0, float(ra))
        except Exception:
            return 5.0

    def _build_headers(self, url: str) -> dict:
        h: dict[str, str] = {
            "User-Agent": "Belel-Grok-Fetcher/1.0 (+policy: %s)" % BELEL_POLICY_URI,
            "X-Belel-License-Id": BELEL_LICENSE_ID,
            "X-Belel-License-SHA256": BELEL_LICENSE_SHA256,
            "X-Belel-Owner": BELEL_OWNER,
            "X-Belel-Policy-URI": BELEL_POLICY_URI,
            "Accept": "application/json, text/plain; q=0.8, */*; q=0.5",
        }
        host = urlparse(url).netloc.lower()
        if "api.github.com" in host or "raw.githubusercontent.com" in host or "github.com" in host:
            if GITHUB_TOKEN:
                h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
                h["Accept"] = "application/vnd.github+json, application/json"
        if "api.twitter.com" in host or host.endswith("x.com"):
            if X_BEARER:
                h["Authorization"] = f"Bearer {X_BEARER}"
        if GENERIC_AUTH and "Authorization" not in h:
            h["Authorization"] = GENERIC_AUTH
        return h
