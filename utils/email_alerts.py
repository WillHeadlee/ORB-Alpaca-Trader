import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
FROM_EMAIL = os.getenv('GMAIL_USER')
FROM_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
TO_EMAIL = os.getenv('ALERT_EMAIL')

def send_alert(subject: str, body: str, priority: str = 'normal') -> None:
    if not all([FROM_EMAIL, FROM_PASSWORD, TO_EMAIL]):
        print(f"[email_alerts] env vars not set, skipping alert: {subject}")
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = TO_EMAIL
        msg['Subject'] = f"[ORB-TRADER] {subject}"
        if priority == 'critical':
            msg['X-Priority'] = '1'
        elif priority == 'high':
            msg['X-Priority'] = '2'
        msg.attach(MIMEText(body, 'html'))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(FROM_EMAIL, FROM_PASSWORD)
            server.send_message(msg)
        print(f"[email_alerts] Alert sent: {subject}")
    except Exception as e:
        print(f"[email_alerts] Failed to send alert: {e}")
