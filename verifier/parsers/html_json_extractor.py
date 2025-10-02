from bs4 import BeautifulSoup
import json, re

def extract_json_from_html(html_bytes: bytes):
    if not html_bytes: return None
    soup = BeautifulSoup(html_bytes, "html.parser")
    for code in soup.select("pre code"):
        txt = code.get_text()
        try: return json.loads(txt)
        except Exception: pass
    for s in soup.find_all("script", type=re.compile("json", re.I)):
        try: return json.loads(s.get_text())
        except Exception: pass
    return None
