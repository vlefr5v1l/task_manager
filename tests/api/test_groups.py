import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import UserRole
from tests.utils import random_string, create_test_user, get_async_auth_headers


@pytest.mark.asyncio
async def test_create_group_as_admin(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует создание группы администратором."""
    admin_user = await create_test_user(db_session, role=UserRole.ADMIN)
    headers = await get_async_auth_headers(async_client, admin_user.email, "testpassword")

    group_data = {
        "name": f"Test Group {random_string(5)}",
        "description": "Test group description"
    }

    response = await async_client.post("/api/v1/groups/", json=group_data, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == group_data["name"]
    assert data["description"] == group_data["description"]


@pytest.mark.asyncio
async def test_create_group_as_team_lead(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует создание группы тимлидом."""
    team_lead = await create_test_user(db_session, role=UserRole.TEAM_LEAD)
    headers = await get_async_auth_headers(async_client, team_lead.email, "testpassword")

    group_data = {
        "name": f"Lead Group {random_string(5)}",
        "description": "Team lead's group"
    }

    response = await async_client.post("/api/v1/groups/", json=group_data, headers=headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_group_as_developer(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует создание группы разработчиком (должно быть запрещено)."""
    dev_user = await create_test_user(db_session, role=UserRole.DEVELOPER)
    headers = await get_async_auth_headers(async_client, dev_user.email, "testpassword")

    group_data = {
        "name": f"Dev Group {random_string(5)}",
        "description": "Developer's group"
    }

    response = await async_client.post("/api/v1/groups/", json=group_data, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_groups(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует получение списка групп."""
    user = await create_test_user(db_session)
    headers = await get_async_auth_headers(async_client, user.email, "testpassword")

    response = await async_client.get("/api/v1/groups/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)