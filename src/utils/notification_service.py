import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.core.config import settings

logger = logging.getLogger(__name__)


def send_notification(user_email, subject, message):
    """
    Отправляет уведомление по email
    В реальном проекте здесь может быть интеграция с сервисом отправки email
    """
    logger.info(f"Sending notification to {user_email}: {subject}")

    # В режиме разработки просто логируем сообщение
    if settings.ENVIRONMENT == "development":
        logger.info(f"Email content: {message}")
        return

    # В реальной среде можно настроить SMTP
    try:
        # Настройка SMTP-клиента (замените на реальные данные)
        # smtp_server = "smtp.example.com"
        # smtp_port = 587
        # smtp_username = "your_username"
        # smtp_password = "your_password"

        # msg = MIMEMultipart()
        # msg["From"] = "noreply@taskmanagement.com"
        # msg["To"] = user_email
        # msg["Subject"] = subject
        # msg.attach(MIMEText(message, "plain"))

        # server = smtplib.SMTP(smtp_server, smtp_port)
        # server.starttls()
        # server.login(smtp_username, smtp_password)
        # server.send_message(msg)
        # server.quit()

        logger.info(f"===== NOTIFICATION =====")
        logger.info(f"TO: {user_email}")
        logger.info(f"SUBJECT: {subject}")
        logger.info(f"MESSAGE: {message}")
        logger.info(f"=======================")
        logger.info(f"Would send email to {user_email} with subject '{subject}'")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
