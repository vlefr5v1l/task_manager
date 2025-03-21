import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import UserRole
from src.models.group import Group, GroupMember, GroupRole
from tests.utils import random_string, create_test_user, get_auth_headers


async def create_test_group(db: AsyncSession, name: str = None) -> Group:
    """Создает тестовую группу в БД."""
    if name is None:
        name = f"Test Group {random_string(5)}"

    group = Group(name=name, description="Test group for projects")
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def add_user_to_group(
    db: AsyncSession, user_id: int, group_id: int, role: GroupRole = GroupRole.DEVELOPER
) -> GroupMember:
    """Добавляет пользователя в группу с указанной ролью."""
    group_member = GroupMember(user_id=user_id, group_id=group_id, role=role)
    db.add(group_member)
    await db.commit()
    await db.refresh(group_member)
    return group_member


@pytest.mark.asyncio
async def test_create_project(client: TestClient, db_session: AsyncSession):
    """Тестирует создание проекта тимлидом группы."""
    # Создаем пользователя и группу
    user = await create_test_user(db_session, role=UserRole.TEAM_LEAD)
    group = await create_test_group(db_session)

    # Добавляем пользователя в группу как тимлида
    await add_user_to_group(db_session, user.id, group.id, GroupRole.TEAM_LEAD)

    # Получаем токен авторизации
    headers = get_auth_headers(client, user.email, "testpassword")

    # Создаем проект
    project_data = {
        "name": f"Test Project {random_string(5)}",
        "description": "Test project description",
        "group_id": group.id,
    }

    response = client.post("/api/v1/projects/", json=project_data, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == project_data["name"]
    assert data["group_id"] == group.id


@pytest.mark.asyncio
async def test_get_projects(client: TestClient, db_session: AsyncSession):
    """Тестирует получение списка проектов."""
    user = await create_test_user(db_session)
    headers = get_auth_headers(client, user.email, "testpassword")

    response = client.get("/api/v1/projects/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_projects_by_group(client: TestClient, db_session: AsyncSession):
    """Тестирует получение проектов фильтрованных по группе."""
    # Создаем пользователя, группу и добавляем пользователя в группу
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)

    headers = get_auth_headers(client, user.email, "testpassword")

    response = client.get(f"/api/v1/projects/?group_id={group.id}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
