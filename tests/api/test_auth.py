import pytest
import httpx
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils import random_string, random_email, create_test_user, get_async_auth_headers


@pytest.mark.asyncio
async def test_register_user(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует регистрацию нового пользователя."""
    user_data = {
        "username": random_string(),
        "email": random_email(),
        "password": "testpassword",
        "full_name": "Test User",
    }

    response = await async_client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200

    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "password" not in data


@pytest.mark.asyncio
async def test_login_user(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует авторизацию пользователя."""
    # Используем текущий цикл событий
    loop = asyncio.get_event_loop()

    # Создаем тестового пользователя
    password = "testpassword"
    user = await create_test_user(db_session, password=password)

    # Выполняем авторизацию
    login_data = {"username": user.email, "password": password}
    response = await async_client.post("/api/v1/auth/login", data=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_incorrect_password(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует авторизацию с неправильным паролем."""
    # Используем текущий цикл событий
    loop = asyncio.get_event_loop()

    # Создаем тестового пользователя
    user = await create_test_user(db_session, password="testpassword")

    # Выполняем авторизацию с неправильным паролем
    login_data = {"username": user.email, "password": "wrongpassword"}
    response = await async_client.post("/api/v1/auth/login", data=login_data)

    assert response.status_code == 401
