from __future__ import annotations
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional
from app.config import EMAIL_FROM, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_USE_TLS, EMAIL_STUB

logger = logging.getLogger("email")

class EmailService:
    def __init__(self) -> None:
        pass

    def send(self, to: str, subject: str, body: str) -> None:
        if EMAIL_STUB or not SMTP_HOST or not EMAIL_FROM:
            logger.info(f"[EMAIL STUB] to={to} subject={subject}\n{body}")
            return
        msg = EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if EMAIL_USE_TLS:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT or 587) as s:
                s.starttls()
                if SMTP_USER:
                    s.login(SMTP_USER, SMTP_PASS or "")
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT or 25) as s:
                if SMTP_USER:
                    s.login(SMTP_USER, SMTP_PASS or "")
                s.send_message(msg)
