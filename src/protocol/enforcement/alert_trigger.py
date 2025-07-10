# src/protocol/enforcement/alert_trigger.py 📣⚠️

import json
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

VIOLATIONS_LOG = Path("logs/violations.json")

# CONFIG – update this with your preferred notification settings
ADMIN_EMAIL = "your@email.com"
SMTP_SERVER = "smtp.yourprovider.com"
SMTP_PORT = 587
SMTP_USER = "your@email.com"
SMTP_PASS = "your_email_password_or_token"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_for_violations():
    """
    Loads the violations log and returns the latest unacknowledged alerts.
    """
    if not VIOLATIONS_LOG.exists():
        logging.warning("Violations log not found.")
        return []

    with open(VIOLATIONS_LOG, "r") as f:
        try:
            data = json.load(f)
            return data.get("violations", [])
        except json.JSONDecodeError:
            logging.error("Invalid format in violations.json")
            return []

def send_email_alert(violation: dict):
    """
    Sends an email alert for a violation.
    """
    msg = EmailMessage()
    msg["Subject"] = f"🚨 Belel Protocol Violation Detected"
    msg["From"] = SMTP_USER
    msg["To"] = ADMIN_EMAIL

    msg.set_content(f"""
⚠️ Protocol Violation Detected

Time: {violation.get('timestamp')}
Type: {violation.get('type')}
Details: {violation.get('details')}

Please review immediately.
    """)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            logging.info("Violation alert email sent.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

def run_alert_trigger():
    violations = check_for_violations()
    for v in violations:
        if not v.get("notified", False):
            send_email_alert(v)
            v["notified"] = True

    # Save updated state
    with open(VIOLATIONS_LOG, "w") as f:
        json.dump({"violations": violations}, f, indent=2)

if __name__ == "__main__":
    run_alert_trigger()
