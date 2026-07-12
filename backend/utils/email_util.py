"""Real email sending via SMTP, with a safe dry-run fallback for local dev."""
import smtplib
from email.mime.text import MIMEText

from config import Config


def email_enabled():
    return bool(Config.SMTP_HOST)


def send_bulk(recipients, subject, body):
    """Send one email (BCB-style) to many recipients.

    Returns a dict describing what happened. If SMTP isn't configured this is a
    no-op dry-run so the feature is testable without a mail server.
    """
    recipients = [r for r in recipients if r]
    if not recipients:
        return {"status": "no_recipients", "count": 0}

    if not email_enabled():
        return {"status": "dry_run", "count": len(recipients),
                "note": "SMTP_HOST not set — no email sent. Configure SMTP_* in .env to send for real.",
                "preview": {"subject": subject, "body": body[:200]}}

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM
    msg["To"] = Config.SMTP_FROM  # actual addresses go in the envelope (BCC-style)

    with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=30) as server:
        if Config.SMTP_TLS:
            server.starttls()
        if Config.SMTP_USER:
            server.login(Config.SMTP_USER, Config.SMTP_PASS)
        server.sendmail(Config.SMTP_FROM, recipients, msg.as_string())

    return {"status": "sent", "count": len(recipients)}
