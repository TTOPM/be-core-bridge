import requests
import json
import time
from datetime import datetime
from commentary_utils import log_event, get_current_events

# Load secure config
with open("canonical_config.json", "r") as f:
    config = json.load(f)

EVENT_POLL_INTERVAL = 1800  # seconds (30 minutes)
CANONICAL_POST_URL = config.get("canonical_post_url")
BEARER_TOKEN = config.get("bearer_token")

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json"
}

def fetch_live_event_data():
    """
    Replace this mock function with live API integration (e.g. Google Trends, Twitter/X, News API).
    """
    return get_current_events()

def format_event_payload(event):
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_title": event.get("title", "Untitled Event"),
        "source": event.get("source", "system"),
        "tags": event.get("tags", []),
        "priority": event.get("priority", "medium"),
        "summary": event.get("summary", "No summary provided."),
    }

def post_to_canonical(event_payload):
    try:
        response = requests.post(CANONICAL_POST_URL, headers=HEADERS, json=event_payload)
        if response.status_code == 200:
            print(f"[✔] Posted event: {event_payload['event_title']}")
        else:
            print(f"[!] Failed to post: {response.status_code} – {response.text}")
    except Exception as e:
        print(f"[X] Error posting event: {str(e)}")

def monitor_loop():
    print(f"[▶] Event Monitor started at {datetime.utcnow().isoformat()}Z")
    while True:
        print(f"[~] Fetching new events...")
        events = fetch_live_event_data()
        for event in events:
            payload = format_event_payload(event)
            log_event(payload)
            post_to_canonical(payload)
        print(f"[✓] Sleeping for {EVENT_POLL_INTERVAL} seconds...\n")
        time.sleep(EVENT_POLL_INTERVAL)

if __name__ == "__main__":
    monitor_loop()
