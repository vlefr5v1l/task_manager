"""
Mock implementations of services for testing.
This module provides mock classes for database and external services.
"""
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic
from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

# Generic type for our model classes
T = TypeVar('T')
ID = TypeVar('ID')


class MockRepository(Generic[T, ID]):
    """
    Generic mock repository for testing.
    Simulates database operations without hitting an actual database.
    """

    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
        self.items: Dict[ID, T] = {}
        self.id_counter = 1

    async def get(self, id: ID) -> Optional[T]:
        """Mock retrieval of an item by ID"""
        return self.items.get(id)

    async def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """Mock retrieval of an item by a specific field"""
        for item in self.items.values():
            if getattr(item, field, None) == value:
                return item
        return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Mock retrieval of multiple items with pagination"""
        all_items = list(self.items.values())
        return all_items[skip:skip + limit]

    async def create(self, item: T) -> T:
        """Mock creation of an item"""
        setattr(item, 'id', self.id_counter)
        self.items[self.id_counter] = item
        self.id_counter += 1
        return item

    async def update(self, id: ID, item: T) -> Optional[T]:
        """Mock update of an existing item"""
        if id not in self.items:
            return None
        self.items[id] = item
        return item

    async def delete(self, id: ID) -> bool:
        """Mock deletion of an item"""
        if id in self.items:
            del self.items[id]
            return True
        return False


class MockRedisCache:
    """
    Mock implementation of Redis cache.
    Simulates Redis operations without requiring an actual Redis instance.
    """

    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.ttls: Dict[str, int] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Mock retrieval from cache"""
        return self.cache.get(key)

    async def set(self, key: str, value: Any, expires: int = 3600) -> bool:
        """Mock setting a value in cache with expiration"""
        self.cache[key] = value
        self.ttls[key] = expires
        return True

    async def delete(self, key: str) -> bool:
        """Mock deletion from cache"""
        if key in self.cache:
            del self.cache[key]
            if key in self.ttls:
                del self.ttls[key]
            return True
        return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Mock invalidation of keys matching a pattern"""
        # Simple implementation that only matches exact prefix
        count = 0
        keys_to_delete = []

        for key in self.cache.keys():
            if key.startswith(pattern.replace("*", "")):
                keys_to_delete.append(key)
                count += 1

        for key in keys_to_delete:
            await self.delete(key)

        return count


class MockKafkaProducer:
    """
    Mock implementation of Kafka producer.
    Records sent messages for verification in tests.
    """

    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.started = False

    async def start(self) -> None:
        """Mock start of Kafka producer"""
        self.started = True

    async def stop(self) -> None:
        """Mock stop of Kafka producer"""
        self.started = False

    async def send_and_wait(self, topic: str, message: Any) -> None:
        """Mock sending a message to Kafka"""
        if not self.started:
            raise RuntimeError("Producer not started")

        self.sent_messages.append({
            "topic": topic,
            "message": message
        })

    def clear(self) -> None:
        """Clear the record of sent messages"""
        self.sent_messages = []


class AsyncMock(MagicMock):
    """Subclass of MagicMock that works with async functions"""

    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


# Patch functions for common services
def patch_redis():
    """Create a patch for Redis cache"""
    mock_redis = MockRedisCache()

    patch_get_cache = patch('src.cache.client.get_cache',
                            side_effect=mock_redis.get)
    patch_set_cache = patch('src.cache.client.set_cache',
                            side_effect=mock_redis.set)
    patch_delete_cache = patch('src.cache.client.delete_cache',
                               side_effect=mock_redis.delete)
    patch_invalidate_pattern = patch('src.cache.client.invalidate_pattern',
                                     side_effect=mock_redis.invalidate_pattern)

    return mock_redis, [patch_get_cache, patch_set_cache,
                        patch_delete_cache, patch_invalidate_pattern]


def patch_kafka():
    """Create a patch for Kafka producer"""
    mock_kafka = MockKafkaProducer()


    #TODO исправить патчи
    patches = [
        # Оригинальные патчи
        patch('src.messaging.producers.get_kafka_producer', return_value=mock_kafka),
        patch('src.messaging.producers.send_event', side_effect=lambda topic, event_type, data:
        mock_kafka.send_and_wait(topic, {"event_type": event_type, "data": data})),

        patch('src.services.task.send_event', side_effect=lambda topic, event_type, data:
        mock_kafka.send_and_wait(topic, {"event_type": event_type, "data": data})),
    ]

    return mock_kafka, patches


def mock_db_session():
    """Create a mock database session"""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    # Mock the execute method to allow customization in tests
    mock_session.execute = AsyncMock()

    return mock_session


# Helper functions to use in tests
async def mock_execute_with_first_result(session_mock, result):
    """Set up session mock to return a specific result as 'first()'"""
    result_mock = MagicMock()
    result_mock.scalars().first.return_value = result
    session_mock.execute.return_value = result_mock


async def mock_execute_with_all_results(session_mock, results):
    """Set up session mock to return specific results as 'all()'"""
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = results
    session_mock.execute.return_value = result_mock