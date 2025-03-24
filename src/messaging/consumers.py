import json
import logging
import asyncio
from aiokafka import AIOKafkaConsumer
from src.core.config import settings
from src.worker.tasks import send_notification

logger = logging.getLogger(__name__)


async def consume_task_events():
    """
    Потребляет события задач из Kafka и обрабатывает их
    """
    consumer = AIOKafkaConsumer(
        "task_events",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="task_management_group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    await consumer.start()
    try:
        async for msg in consumer:
            logger.info(f"Received message: {msg.value}")
            event = msg.value

            if event["event_type"] == "task_created":
                task_data = event["data"]
                # Например, отправляем уведомление о новой задаче
                if task_data.get("assigned_to_email"):
                    send_notification.delay(
                        user_email=task_data["assigned_to_email"],
                        subject=f"Вам назначена новая задача: {task_data['title']}",
                        message=f"Вам назначена новая задача '{task_data['title']}'. "
                        + f"Приоритет: {task_data['priority']}. "
                        + f"Описание: {task_data['description']}",
                    )

            elif event["event_type"] == "task_updated":
                task_data = event["data"]
                if task_data.get("assigned_to_email"):
                    send_notification.delay(
                        user_email=task_data["assigned_to_email"],
                        subject=f"Задача обновлена: {task_data['title']}",
                        message=f"Задача '{task_data['title']}' была обновлена. "
                        + f"Новый статус: {task_data.get('status', 'не изменен')}.",
                    )

            elif event["event_type"] == "comment_added":
                comment_data = event["data"]
                # Например, отправляем уведомление о новом комментарии
                for email in comment_data.get("notify_emails", []):
                    send_notification.delay(
                        user_email=email,
                        subject=f"Новый комментарий к задаче: {comment_data['task_title']}",
                        message=f"К задаче '{comment_data['task_title']}' добавлен новый комментарий: "
                        + f"{comment_data['content']}",
                    )
    finally:
        await consumer.stop()


async def start_consumers():
    """
    Запускает все консьюмеры Kafka
    """
    await asyncio.gather(
        consume_task_events(),
    )
