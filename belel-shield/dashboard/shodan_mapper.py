import os, requests
def query_shodan(host):
    key=os.environ.get("SHODAN_API")
    if not key: raise RuntimeError("No SHODAN_API set")
    url=f"https://api.shodan.io/shodan/host/{host}?key={key}"
    r=requests.get(url, timeout=10); r.raise_for_status()
    return r.json()
