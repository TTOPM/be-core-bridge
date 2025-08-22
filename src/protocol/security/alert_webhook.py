# src/protocol/security/alert_webhook.py

import requests
from datetime import datetime

class WebhookAlerter:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, title: str, message: str):
        payload = {
            "content": f"🚨 **{title}**\n🕒 {datetime.now().isoformat()}\n```\n{message}\n```"
        }
        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"[ALERT FAILURE] Could not send webhook alert: {e}")
