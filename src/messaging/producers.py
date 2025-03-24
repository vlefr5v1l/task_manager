import json
import logging
from typing import Any, Dict
from aiokafka import AIOKafkaProducer
import asyncio

from src.core.config import settings

logger = logging.getLogger(__name__)

producer = None


async def get_kafka_producer():
    """
    Возвращает инстанс Kafka-продюсера или создает новый, если его нет
    """
    global producer
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS, value_serializer=lambda v: json.dumps(v).encode("utf-8")
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
