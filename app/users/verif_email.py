import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

def send_verification_email(to_email: str, token: str):
    """
    Отправляет письмо с ссылкой подтверждения
    """
    verification_link = f"http://localhost:8000/auth/verify-email?token={token}"

    msg = MIMEMultipart()
    msg['Subject'] = "Подтвердите ваш email"
    msg['From'] = settings.EMAIL_SENDER
    msg['To'] = to_email

    body = f"""
    Привет!

    Пожалуйста, подтвердите ваш email, перейдя по ссылке:
    {verification_link}

    Ссылка действительна 24 часа.
    """
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)