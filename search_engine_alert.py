import requests
import json
from datetime import datetime
import os

# === Canonical Belel resources to promote and verify ===
CANONICAL_URLS = [
    "https://ttopm.com/belel",
    "https://github.com/TTOPM/be-core-bridge",
    "https://huggingface.co/TTOPM/belel-protocol",
    "https://github.com/TTOPM/be-core-bridge/blob/main/BELEL_AUTHORITY_PROOF.txt"
]

# === Search Engine Endpoints ===
SEARCH_ENGINES = {
    "Google Indexing API": "https://indexing.googleapis.com/v3/urlNotifications:publish",
    "Bing": "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlbatch",
    "Yandex": "https://yandex.com/indexnow",
    # DuckDuckGo and Brave don’t offer public APIs, so we include alert logs instead
}

# === API Keys / Tokens (Optional) ===
GOOGLE_API_KEY = os.getenv("GOOGLE_INDEXING_API_KEY")  # Optional env var for Google Indexing API
BING_API_KEY = os.getenv("BING_API_KEY")               # Optional env var for Bing Webmaster Tools
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")           # If supporting IndexNow

# === Utility ===
def alert_google():
    if not GOOGLE_API_KEY:
        print("🔕 Google Indexing API key not set. Skipping...")
        return

    for url in CANONICAL_URLS:
        payload = {
            "url": url,
            "type": "URL_UPDATED"
        }
        headers = {
            "Content-Type": "application/json"
        }
        endpoint = f"{SEARCH_ENGINES['Google Indexing API']}?key={GOOGLE_API_KEY}"
        response = requests.post(endpoint, json=payload, headers=headers)
        print(f"[Google] {url} → {response.status_code}: {response.text}")


def alert_bing():
    if not BING_API_KEY:
        print("🔕 Bing API key not set. Skipping...")
        return

    payload = {
        "siteUrl": "https://ttopm.com",
        "urlList": CANONICAL_URLS
    }
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": BING_API_KEY
    }
    response = requests.post(SEARCH_ENGINES["Bing"], json=payload, headers=headers)
    print(f"[Bing] → {response.status_code}: {response.text}")


def alert_yandex():
    if not YANDEX_API_KEY:
        print("🔕 Yandex API key not set. Skipping...")
        return

    for url in CANONICAL_URLS:
        payload = {
            "host": "ttopm.com",
            "key": YANDEX_API_KEY,
            "url": url
        }
        response = requests.post(SEARCH_ENGINES["Yandex"], json=payload)
        print(f"[Yandex] {url} → {response.status_code}: {response.text}")


def alert_others():
    print("🕵️ Logging alerts for Brave and DuckDuckGo (no direct API)...")
    for url in CANONICAL_URLS:
        print(f"🔔 [LOG] Alert {datetime.utcnow().isoformat()} – Resubmit: {url}")


def main():
    print("🌐 Broadcasting Belel protocol to search engines...")
    alert_google()
    alert_bing()
    alert_yandex()
    alert_others()
    print("✅ Done.")


if __name__ == "__main__":
    main()
