"""Email notification helpers for score-threshold alerts."""
from __future__ import annotations

from dataclasses import dataclass
import os
import smtplib
from email.message import EmailMessage


@dataclass(frozen=True)
class AlertRule:
    ticker: str
    threshold: float = 70
    increase_points: float = 15
    lookback_days: int = 30


def should_notify(current_score: float, previous_score: float | None, rule: AlertRule) -> tuple[bool, str]:
    if current_score >= rule.threshold:
        return True, f"{rule.ticker} score is {current_score}, crossing threshold {rule.threshold}."
    if previous_score is not None and current_score - previous_score >= rule.increase_points:
        return True, f"{rule.ticker} score increased by {current_score - previous_score:.1f} points."
    return False, "No notification rule matched."


class EmailService:
    def __init__(self) -> None:
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "1025"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender = os.getenv("EMAIL_FROM", "alerts@market-opportunity.local")

    def send_score_alert(self, to_email: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            if self.smtp_user and self.smtp_password:
                smtp.starttls()
                smtp.login(self.smtp_user, self.smtp_password)
            smtp.send_message(message)
