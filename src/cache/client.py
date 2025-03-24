import json
from typing import Any, Optional
import redis.asyncio as redis
from src.core.config import settings

# Создаем Redis-клиент
redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True)


async def get_cache(key: str) -> Optional[Any]:
    """
    Получает данные из кэша по ключу
    """
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None


async def set_cache(key: str, value: Any, expires: int = 3600) -> bool:
    """
    Устанавливает данные в кэш с указанным временем жизни (по умолчанию 1 час)
    """
    serialized = json.dumps(value)
    return await redis_client.set(key, serialized, ex=expires)


async def delete_cache(key: str) -> bool:
    """
    Удаляет данные из кэша по ключу
    """
    return await redis_client.delete(key)


async def invalidate_pattern(pattern: str) -> int:
    """
    Удаляет все ключи, соответствующие шаблону
    """
    keys = await redis_client.keys(pattern)
    if keys:
        return await redis_client.delete(*keys)
    return 0
