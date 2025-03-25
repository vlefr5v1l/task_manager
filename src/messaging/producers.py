import json
import logging
from typing import Any, Dict, List
from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
import asyncio

from src.core.config import settings

logger = logging.getLogger(__name__)

# Список топиков, которые нужно создать
KAFKA_TOPICS = [
    "task_events",
    "notification_events"
]

producer = None

async def create_topics():
    """
    Создает необходимые топики в Kafka, если они не существуют
    """
    try:
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
        )
        await admin_client.start()

        # Получаем список существующих топиков
        existing_topics = await admin_client.list_topics()
        logger.info(f"Existing Kafka topics: {existing_topics}")

        # Создаем только те топики, которых еще нет
        topics_to_create = []
        for topic in KAFKA_TOPICS:
            if topic not in existing_topics:
                topics_to_create.append(
                    NewTopic(
                        name=topic,
                        num_partitions=1,
                        replication_factor=1  # Для одного брокера
                    )
                )

        if topics_to_create:
            logger.info(f"Creating Kafka topics: {[t.name for t in topics_to_create]}")
            await admin_client.create_topics(topics_to_create)
            logger.info("Kafka topics created successfully")
        else:
            logger.info("All Kafka topics already exist")

    except Exception as e:
        logger.error(f"Failed to create Kafka topics: {e}")
    finally:
        await admin_client.close()

async def get_kafka_producer():
    """
    Возвращает инстанс Kafka-продюсера или создает новый, если его нет
    """
    global producer
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await producer.start()
    return producer

async def close_kafka_producer():
    """
    Закрывает соединение с Kafka
    """
    global producer
    if producer is not None:
        await producer.stop()
        producer = None

async def send_event(topic: str, event_type: str, data: Dict[str, Any]):
    """
    Отправляет событие в Kafka
    """
    try:
        producer = await get_kafka_producer()

        # Формируем сообщение
        message = {"event_type": event_type, "data": data}

        # Отправляем сообщение
        await producer.send_and_wait(topic, message)
        logger.info(f"Sent event to topic {topic}: {event_type}")
    except Exception as e:
        logger.error(f"Failed to send Kafka event: {e}")