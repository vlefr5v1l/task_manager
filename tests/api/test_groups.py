import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import UserRole
from tests.utils import random_string, create_test_user, get_auth_headers


@pytest.mark.asyncio
async def test_create_group_as_admin(client: TestClient, db_session: AsyncSession):
    """Тестирует создание группы администратором."""
    admin_user = await create_test_user(db_session, role=UserRole.ADMIN)
    headers = get_auth_headers(client, admin_user.email, "testpassword")

    group_data = {
        "name": f"Test Group {random_string(5)}",
        "description": "Test group description",
    }

    response = client.post("/api/v1/groups/", json=group_data, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == group_data["name"]
    assert data["description"] == group_data["description"]


@pytest.mark.asyncio
async def test_create_group_as_team_lead(client: TestClient, db_session: AsyncSession):
    """Тестирует создание группы тимлидом."""
    team_lead = await create_test_user(db_session, role=UserRole.TEAM_LEAD)
    headers = get_auth_headers(client, team_lead.email, "testpassword")

    group_data = {
        "name": f"Lead Group {random_string(5)}",
        "description": "Team lead's group",
    }

    response = client.post("/api/v1/groups/", json=group_data, headers=headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_group_as_developer(client: TestClient, db_session: AsyncSession):
    """Тестирует создание группы разработчиком (должно быть запрещено)."""
    dev_user = await create_test_user(db_session, role=UserRole.DEVELOPER)
    headers = get_auth_headers(client, dev_user.email, "testpassword")

    group_data = {
        "name": f"Dev Group {random_string(5)}",
        "description": "Developer's group",
    }

    response = client.post("/api/v1/groups/", json=group_data, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_groups(client: TestClient, db_session: AsyncSession):
    """Тестирует получение списка групп."""
    user = await create_test_user(db_session)
    headers = get_auth_headers(client, user.email, "testpassword")

    response = client.get("/api/v1/groups/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
