import logging
from typing import Optional
from aiosmtplib import send
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)

async def send_verification_email(email: str, token: str):
    verify_url = f"{settings.BASE_URL}/auth/verify?token={token}"
    body = (
        "Добро пожаловать в Game Suggestions!\n\n"
        "Подтвердите свою почту, перейдя по ссылке ниже:\n"
        f"{verify_url}\n\n"
        "Если вы не регистрировались, просто проигнорируйте это письмо.\n\n"
        "С уважением,\nКоманда Game Suggestions"
    )

    if not settings.SMTP_HOST:
        logger.info(f"Верификационное письмо для {email}: {verify_url}")
        return

    message = EmailMessage()
    message["From"] = f"Game Suggestions No-Reply <{settings.SMTP_FROM}>"
    message["To"] = email
    message["Subject"] = "Подтверждение регистрации Game Suggestions"
    message.set_content(body)

    try:
        if settings.SMTP_PORT == 465:
            await send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=True,  # SSL для порта 465
            )
        else:
            await send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,  # STARTTLS для остальных
            )
        logger.info(f"Письмо отправлено на {email}")
    except Exception as e:
        logger.error(f"Ошибка отправки письма: {e}")
        logger.info(f"Ссылка для подтверждения (дубль): {verify_url}")
