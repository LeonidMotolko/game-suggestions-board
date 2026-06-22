import logging
from typing import Optional
from aiosmtplib import send
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)

async def send_verification_email(email: str, token: str):
    """Отправляет письмо для подтверждения email. Если SMTP не настроен, выводит ссылку в лог."""
    verify_url = f"{settings.BASE_URL}/auth/verify?token={token}"
    body = f"Для подтверждения email перейдите по ссылке: {verify_url}"

    if not settings.SMTP_HOST:
        logger.info(f"Верификационное письмо для {email}: {verify_url}")
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = email
    message["Subject"] = "Подтверждение регистрации Game Suggestions"
    message.set_content(body)

    try:
        await send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info(f"Письмо отправлено на {email}")
    except Exception as e:
        logger.error(f"Ошибка отправки письма: {e}")
        logger.info(f"Ссылка для подтверждения (дубль): {verify_url}")
