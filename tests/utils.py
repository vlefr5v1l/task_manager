import random
import string
import asyncio
from typing import Dict, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserRole
from src.validator.security import get_password_hash


def random_string(length: int = 10) -> str:
    """Генерирует случайную строку заданной длины."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    """Генерирует случайный email."""
    return f"{random_string(8)}@{random_string(6)}.com"


async def create_test_user(
    db: AsyncSession, role: UserRole = UserRole.DEVELOPER, password: str = "testpassword"
) -> User:
    """Создает тестового пользователя в БД."""
    user = User(
        username=random_string(),
        email=random_email(),
        password_hash=get_password_hash(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_async_auth_headers(client: httpx.AsyncClient, email: str, password: str) -> Dict[str, str]:
    """Выполняет асинхронную авторизацию и возвращает заголовки с токеном."""
    login_data = {"username": email, "password": password}

    # Убедимся, что мы работаем в текущем цикле событий
    current_loop = asyncio.get_event_loop()

    # Выполняем запрос в текущем цикле событий
    response = await client.post("/api/v1/auth/login", data=login_data)

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
