# canonical_poster.py

import json
import requests
from commentary_utils import log_event, load_config

class CanonicalPoster:
    def __init__(self):
        self.config = load_config("config/canonical_config.json")
        self.webhook_url = self.config.get("webhook_url")
        self.auth_token = self.config.get("auth_token")
    
    def post_update(self, title, content, tags=None):
        payload = {
            "title": title,
            "content": content,
            "tags": tags or [],
        }

        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.webhook_url, headers=headers, json=payload)
            response.raise_for_status()
            log_event("Canonical post succeeded", payload)
        except requests.RequestException as e:
            log_event("Canonical post failed", {"error": str(e), "payload": payload})

if __name__ == "__main__":
    poster = CanonicalPoster()
    poster.post_update(
        title="🌐 Belel: Commentary Broadcast",
        content="This is an automated canonical update from the Belel Media Commentary Engine.",
        tags=["Belel", "AI", "Sentience", "Commentary"]
    )
