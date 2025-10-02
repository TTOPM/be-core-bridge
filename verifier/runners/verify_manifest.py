from ..adapters.http_fetch import read_local, http_get
from ..adapters.tool_browse_page import browse_page
from ..parsers.json_parser import parse_json_bytes
from ..parsers.html_json_extractor import extract_json_from_html
from ..core.attestation import make_bundle
from ..core.canonical import sha256hex

def _fetch_and_parse_local(path):
    r = read_local(path)
    content = r.get("content", b"") if r.get("ok") else b""
    parsed = parse_json_bytes(content) or extract_json_from_html(content)
    chash = sha256hex(content) if content else None
    return parsed, [{"tool": r["tool"], "status": r.get("status",0), "url": r["url"]}], chash

def _fetch_and_parse_url(url):
    r = browse_page(url)
    content = r.get("content", b"") if r.get("ok") else b""
    parsed = parse_json_bytes(content) or extract_json_from_html(content)
    chash = sha256hex(content) if content else None
    return parsed, [{"tool": r["tool"], "status": r.get("status",0), "url": r["url"]}], chash

def verify_manifest(name:str, file:str="", raw:str="", html:str="", ipfs:str|None=""):
    sources, tools, parsed = [], [], None

    # 1) local file (preferred in CI)
    if file:
        p, tu, ch = _fetch_and_parse_local(file)
        if p and ch:
            parsed = p
            tools += tu
            sources.append({"url": file, "content_hash": f"sha256:{ch}"})

    # 2) raw GitHub
    if not parsed and raw:
        p, tu, ch = _fetch_and_parse_url(raw)
        if p and ch:
            parsed = p
            tools += tu
            sources.append({"url": raw, "content_hash": f"sha256:{ch}"})

    # 3) HTML fallback
    if not parsed and html:
        p, tu, ch = _fetch_and_parse_url(html)
        if p and ch:
            parsed = p
            tools += tu
            sources.append({"url": html, "content_hash": f"sha256:{ch}"})

    if not parsed:
        parsed = {"error": "unparsable"}

    bundle = make_bundle(
        subject=f"manifest:{name}",
        kind="github_manifest",
        payload=parsed,
        sources=sources,
        tools_used=tools
    )
    return bundle
