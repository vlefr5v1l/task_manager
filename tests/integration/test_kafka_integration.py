"""
Integration tests for Kafka messaging.
Tests the interaction between producers and consumers.
"""
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest

from src.messaging.producers import send_event
from src.messaging.consumers import consume_task_events
from src.models.task import TaskStatus, TaskPriority


@pytest.mark.asyncio
async def test_send_event(mock_kafka):
    """Test sending an event to Kafka."""
    # Arrange
    topic = "task_events"
    event_type = "task_created"
    data = {
        "id": 1,
        "title": "Test Task",
        "description": "Test description",
        "status": TaskStatus.NEW.value,
        "priority": TaskPriority.MEDIUM.value,
        "created_by_id": 1,
        "assigned_to_id": 2,
        "assigned_to_email": "user@example.com",
        "project_id": 1,
    }

    # Act
    await send_event(topic, event_type, data)

    # Assert
    assert len(mock_kafka.sent_messages) == 1
    message = mock_kafka.sent_messages[0]
    assert message["topic"] == topic
    assert message["message"]["event_type"] == event_type
    assert message["message"]["data"] == data


@pytest.mark.asyncio
async def test_task_events_consumer():
    """Test consuming task events from Kafka."""
    # Arrange
    # Create a mock Kafka consumer that will yield one message then stop
    class MockAIOKafkaConsumer:
        def __init__(self, *args, **kwargs):
            self.started = False
            self.message_to_yield = None

        async def start(self):
            self.started = True

        async def stop(self):
            self.started = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.started or self.message_to_yield is None:
                raise StopAsyncIteration

            message = self.message_to_yield
            self.message_to_yield = None
            return message

    mock_consumer = MockAIOKafkaConsumer()

    # Create a mock message
    class MockMessage:
        def __init__(self, topic, value):
            self.topic = topic
            self.value = value
            self.key = None
            self.partition = 0
            self.offset = 0
            self.timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)

    # Create a test event
    event = {
        "event_type": "task_created",
        "data": {
            "id": 1,
            "title": "New Task From Kafka",
            "description": "Task created through Kafka event",
            "status": TaskStatus.NEW.value,
            "priority": TaskPriority.HIGH.value,
            "created_by_id": 1,
            "assigned_to_id": 2,
            "assigned_to_email": "user@example.com",
            "project_id": 1,
        }
    }

    # Set the message to be yielded
    mock_message = MockMessage(
        topic="task_events",
        value=json.dumps(event).encode("utf-8")
    )
    mock_consumer.message_to_yield = mock_message

    # Replace AIOKafkaConsumer with our mock
    with patch('aiokafka.AIOKafkaConsumer', return_value=mock_consumer):
        # Mock the notification function
        with patch('src.worker.tasks.send_notification') as mock_notify:
            # Need to patch import to mock the delay() call on the task
            mock_notify.delay = AsyncMock()

            # Create a task for the consumer to run briefly
            consumer_task = asyncio.create_task(consume_task_events())

            # Allow the consumer to run for a short time
            await asyncio.sleep(0.1)

            # Cancel the task (we don't want it running indefinitely)
            consumer_task.cancel()

            # Try to await it - we expect a CancelledError so we ignore it
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

            # Assert - Check that notification was sent
            mock_notify.delay.assert_called_once()
            # Check the arguments
            call_args = mock_notify.delay.call_args[1]
            assert "user@example.com" in call_args.get("user_email", "")
            assert "New Task From Kafka" in call_args.get("subject", "")


@pytest.mark.asyncio
async def test_multiple_event_types(mock_kafka):
    """Test handling different types of events."""
    # Arrange - Create events of different types
    events = [
        {
            "topic": "task_events",
            "event_type": "task_created",
            "data": {
                "id": 1,
                "title": "Created Task",
                "assigned_to_email": "user1@example.com",
            }
        },
        {
            "topic": "task_events",
            "event_type": "task_updated",
            "data": {
                "id": 1,
                "title": "Updated Task",
                "assigned_to_email": "user1@example.com",
            }
        },
        {
            "topic": "notification_events",
            "event_type": "user_notification",
            "data": {
                "user_id": 1,
                "message": "Test notification",
            }
        }
    ]

    # Act - Send all events
    for event in events:
        await send_event(event["topic"], event["event_type"], event["data"])

    # Assert - Check messages were sent correctly
    assert len(mock_kafka.sent_messages) == 3

    # Check the first message (task_created)
    assert mock_kafka.sent_messages[0]["topic"] == "task_events"
    assert mock_kafka.sent_messages[0]["message"]["event_type"] == "task_created"
    assert mock_kafka.sent_messages[0]["message"]["data"]["title"] == "Created Task"

    # Check the second message (task_updated)
    assert mock_kafka.sent_messages[1]["topic"] == "task_events"
    assert mock_kafka.sent_messages[1]["message"]["event_type"] == "task_updated"
    assert mock_kafka.sent_messages[1]["message"]["data"]["title"] == "Updated Task"

    # Check the third message (user_notification)
    assert mock_kafka.sent_messages[2]["topic"] == "notification_events"
    assert mock_kafka.sent_messages[2]["message"]["event_type"] == "user_notification"
    assert mock_kafka.sent_messages[2]["message"]["data"]["message"] == "Test notification"


@pytest.mark.asyncio
async def test_producer_lifecycle():
    """Test Kafka producer startup and shutdown."""
    # Use patch to mock the Kafka producer
    with patch('src.messaging.producers.AIOKafkaProducer') as MockProducer:
        # Create mock instance
        mock_producer_instance = AsyncMock()
        MockProducer.return_value = mock_producer_instance

        # Mock producer startup
        from src.messaging.producers import get_kafka_producer
        producer = await get_kafka_producer()

        # Assert producer was started
        mock_producer_instance.start.assert_called_once()

        # Test shutdown
        from src.messaging.producers import close_kafka_producer
        await close_kafka_producer()

        # Assert producer was stopped
        mock_producer_instance.stop.assert_called_once()


@pytest.mark.asyncio
async def test_consumer_handles_exceptions():
    """Test that consumer properly handles exceptions."""
    # Create a mock consumer that raises an exception
    class ExceptionRaisingConsumer:
        def __init__(self, *args, **kwargs):
            self.started = False

        async def start(self):
            self.started = True

        async def stop(self):
            self.started = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.started:
                raise StopAsyncIteration

            # Raise exception on first call
            raise RuntimeError("Test exception")

    mock_consumer = ExceptionRaisingConsumer()

    # Mock the consumer
    with patch('aiokafka.AIOKafkaConsumer', return_value=mock_consumer):
        # Mock logging to verify exception is logged
        with patch('logging.getLogger') as mock_logging:
            mock_logger = AsyncMock()
            mock_logging.return_value = mock_logger

            # Start consumer - it should catch the exception and continue
            consumer_task = asyncio.create_task(consume_task_events())

            # Allow the consumer to run briefly
            await asyncio.sleep(0.1)

            # Cancel the task
            consumer_task.cancel()

            # Try to await it - we expect a CancelledError so we ignore it
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

            # Verify error was logged (but consumer didn't crash)
            mock_logger.error.assert_called()