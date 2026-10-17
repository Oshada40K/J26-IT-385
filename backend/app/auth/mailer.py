import os
import smtplib
from email.message import EmailMessage
from urllib.parse import quote, urlsplit

from fastapi import HTTPException


def settings():
    host = os.getenv('AUTH_SMTP_HOST')
    sender = os.getenv('AUTH_SMTP_FROM')
    frontend = os.getenv('AUTH_FRONTEND_URL', '').rstrip('/')
    if not host or not sender or urlsplit(frontend).scheme not in {'http', 'https'}:
        raise HTTPException(503, 'Password reset email is not configured. Please contact the project administrator.')
    return host, sender, frontend


def send_reset(email, token):
    host, sender, frontend = settings()
    message = EmailMessage()
    message['Subject'] = 'Reset your CareerNova password'
    message['From'] = sender
    message['To'] = email
    message.set_content(f'Reset your CareerNova password using this link within 30 minutes:\n\n'
                        f'{frontend}/reset-password#token={quote(token)}\n\n'
                        'If you did not request this, you can ignore this email.')
    with smtplib.SMTP(host, int(os.getenv('AUTH_SMTP_PORT', '587')), timeout=10) as smtp:
        smtp.starttls()
        username = os.getenv('AUTH_SMTP_USERNAME')
        if username:
            smtp.login(username, os.environ['AUTH_SMTP_PASSWORD'])
        smtp.send_message(message)
