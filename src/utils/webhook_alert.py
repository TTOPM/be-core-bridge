import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_webhook_alert(webhook_url: str, payload: dict):
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        logging.info(f"Webhook alert sent. Status: {response.status_code}")
    except Exception as e:
        logging.error(f"Webhook alert failed: {e}")
