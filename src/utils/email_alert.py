import smtplib
from email.mime.text import MIMEText
import logging

def send_email_alert(subject, body, recipient_email, sender_email, smtp_server, smtp_port, smtp_username, smtp_password):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())

        logging.info(f"Email alert sent to {recipient_email}")
    except Exception as e:
        logging.error(f"Failed to send email alert: {e}")
