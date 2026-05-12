"""
Notification channels — email, SMS (Twilio), Discord webhook.
Each channel is opt-in: set the relevant env vars to activate it.

Email  : NOTIFY_EMAIL_TO, NOTIFY_EMAIL_FROM, NOTIFY_EMAIL_PASSWORD
SMS    : NOTIFY_TWILIO_SID, NOTIFY_TWILIO_TOKEN, NOTIFY_TWILIO_FROM, NOTIFY_TWILIO_TO
Discord: NOTIFY_DISCORD_WEBHOOK
"""

import os
import smtplib
import urllib.request
import urllib.parse
import json
from email.mime.text import MIMEText
from typing import Optional

from utils.logger import log


# ---------------------------------------------------------------------------
# Email (Gmail SMTP)
# ---------------------------------------------------------------------------

def _send_email(subject: str, body: str) -> bool:
    to_addr   = os.getenv("NOTIFY_EMAIL_TO")
    from_addr = os.getenv("NOTIFY_EMAIL_FROM")
    password  = os.getenv("NOTIFY_EMAIL_PASSWORD")
    if not all([to_addr, from_addr, password]):
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = to_addr
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as s:
            s.login(from_addr, password)
            s.sendmail(from_addr, [to_addr], msg.as_string())
        log.info(f"Email sent to {to_addr}: {subject}")
        return True
    except Exception as exc:
        log.error(f"Email failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# SMS (Twilio)
# ---------------------------------------------------------------------------

def _send_sms(body: str) -> bool:
    sid   = os.getenv("NOTIFY_TWILIO_SID")
    token = os.getenv("NOTIFY_TWILIO_TOKEN")
    from_ = os.getenv("NOTIFY_TWILIO_FROM")
    to    = os.getenv("NOTIFY_TWILIO_TO")
    if not all([sid, token, from_, to]):
        return False
    try:
        from twilio.rest import Client
        Client(sid, token).messages.create(body=body, from_=from_, to=to)
        log.info(f"SMS sent to {to}")
        return True
    except ImportError:
        log.warning("Twilio not installed — run: pip install twilio")
        return False
    except Exception as exc:
        log.error(f"SMS failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Discord webhook
# ---------------------------------------------------------------------------

def _send_discord(content: str) -> bool:
    webhook = os.getenv("NOTIFY_DISCORD_WEBHOOK")
    if not webhook:
        return False
    try:
        data = json.dumps({"content": content}).encode()
        req  = urllib.request.Request(
            webhook, data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        log.info("Discord notification sent")
        return True
    except Exception as exc:
        log.error(f"Discord failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def notify(subject: str, body: str) -> None:
    """Broadcast to every configured channel (silent if none configured)."""
    _send_email(subject, body)
    _send_sms(f"{subject}\n{body}")
    _send_discord(f"**{subject}**\n{body}")


def notify_trade(action: str, symbol: str, price: float, shares: int,
                 reason: str, pnl: Optional[float] = None) -> None:
    emoji = {"ENTRY": "🟢", "EXIT": "🔴", "SKIP": "⚪"}.get(action, "•")
    pnl_str = f"  P&L: ${pnl:+.2f}" if pnl is not None else ""
    body = (
        f"Action : {action}\n"
        f"Symbol : {symbol}\n"
        f"Price  : ${price:.2f}\n"
        f"Shares : {shares}\n"
        f"Reason : {reason}"
        + (f"\nP&L    : ${pnl:+.2f}" if pnl is not None else "")
    )
    notify(f"{emoji} ORB {action} — {symbol}", body)


def notify_daily_summary(
    date: str,
    total_trades: int,
    win_rate: float,
    net_pnl: float,
    largest_win: float,
    largest_loss: float,
) -> None:
    body = (
        f"Date         : {date}\n"
        f"Total trades : {total_trades}\n"
        f"Win rate     : {win_rate:.1f}%\n"
        f"Net P&L      : ${net_pnl:+.2f}\n"
        f"Largest win  : ${largest_win:+.2f}\n"
        f"Largest loss : ${largest_loss:+.2f}"
    )
    notify(f"📊 ORB Daily Summary — {date}", body)
