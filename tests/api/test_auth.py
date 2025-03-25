import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils import random_string, random_email, create_test_user, get_auth_headers


@pytest.mark.asyncio
async def test_register_user(client: TestClient, db_session: AsyncSession):
    """Тестирует регистрацию нового пользователя."""
    user_data = {
        "username": random_string(),
        "email": random_email(),
        "password": "testpassword",
        "full_name": "Test User"
    }

    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200

    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "password" not in data


@pytest.mark.asyncio
async def test_login_user(client: TestClient, db_session: AsyncSession):
    """Тестирует авторизацию пользователя."""
    password = "testpassword"
    user = await create_test_user(db_session, password=password)

    login_data = {
        "username": user.email,
        "password": password
    }

    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_incorrect_password(client: TestClient, db_session: AsyncSession):
    """Тестирует авторизацию с неправильным паролем."""
    user = await create_test_user(db_session, password="testpassword")

    login_data = {
        "username": user.email,
        "password": "wrongpassword"
    }

    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401