from .http_fetch import http_get
def browse_page(url: str) -> dict:
    # Later, replace with Grok's native tool. For now, use HTTP fallback.
    return http_get(url)
