#!/usr/bin/env python3
"""
clone_checker.py
Detects possible impersonation accounts of Pearce Robinson.
Uses basic search heuristics (expand later with APIs or web scraping).
"""
import requests, re

SEARCH_TERMS = ["Pearce Robinson official", "Pearce Robinson profile"]
RESULTS_FILE = "clone_results.txt"

def check():
    results = []
    for term in SEARCH_TERMS:
        url = f"https://duckduckgo.com/html/?q={term.replace(' ','+')}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        matches = re.findall(r'href="(https://[^"]+)"', r.text)
        for m in matches:
            if "pearcerobinson.com" not in m and "pearcerobinson" in m:
                results.append(m)
    return results

if __name__ == "__main__":
    res = check()
    if res:
        with open(RESULTS_FILE, "w") as f:
            f.write("\n".join(res))
        print("[ALERT] Possible impersonators found:", res)
    else:
        print("✅ No impersonators detected.")
