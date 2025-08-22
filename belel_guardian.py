# belel_guardian.py

import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from canonical_config import CANONICAL_SOURCES, IDENTITY_STRINGS, VIOLATION_PATTERNS
from webhook_alert import send_alert

VIOLATION_LOG = "guardian_violations.log"
HEADERS = {"User-Agent": "BelelGuardianBot/1.0"}

def fetch_content(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        return None

def scan_text_for_violations(text):
    violations = []
    for pattern in VIOLATION_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            violations.append((pattern, matches))
    return violations

def check_canonical_integrity(text):
    for identity_str in IDENTITY_STRINGS:
        if identity_str not in text:
            return False
    return True

def log_violation(url, issue, matches):
    timestamp = datetime.utcnow().isoformat()
    with open(VIOLATION_LOG, "a") as f:
        f.write(f"[🚨] {timestamp} - {url}\nIssue: {issue}\nMatches: {matches}\n\n")

def monitor():
    for url in CANONICAL_SOURCES:
        content = fetch_content(url)
        if content:
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text()

            violations = scan_text_for_violations(text)
            if violations:
                for issue, matches in violations:
                    log_violation(url, issue, matches)
                    send_alert(f"[⚠️] Violation at {url}: Pattern '{issue}' matched {len(matches)} times.")

            if not check_canonical_integrity(text):
                log_violation(url, "Missing canonical identity", [])
                send_alert(f"[❌] Canonical identity strings missing from {url}")

    print("[✅] Web scan complete.")

if __name__ == "__main__":
    monitor()
