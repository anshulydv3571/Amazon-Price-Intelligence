"""Email alerts via smtplib (Gmail SMTP over SSL by default)."""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import config


def send_price_alert(to_email: str, title: str, url: str, price: float,
                     target: float | None) -> None:
    if not (config.SMTP_USER and config.SMTP_PASSWORD):
        raise RuntimeError("SMTP_USER / SMTP_PASSWORD are not set in .env")

    cur = config.CURRENCY
    subject = f"Price drop: {title[:60]} is now {cur}{price:,.0f}"
    target_line = f" (your target: {cur}{target:,.0f})" if target else ""

    text_body = f"{title}\nNow {cur}{price:,.2f}{target_line}\n{url}\n"
    html_body = (
        f"<h3>Price drop on a product you track</h3>"
        f"<p><b>{escape(title)}</b></p>"
        f"<p>Current price: <b>{cur}{price:,.2f}</b>{escape(target_line)}</p>"
        f'<p><a href="{escape(url)}">Open on Amazon</a></p>'
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)
