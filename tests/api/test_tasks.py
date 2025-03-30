import pytest
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import UserRole
from src.models.group import GroupRole
from src.models.project import Project
from src.models.task import TaskStatus, TaskPriority
from tests.utils import random_string, create_test_user, get_async_auth_headers
from tests.api.test_projects import create_test_group, add_user_to_group


async def create_test_project(db: AsyncSession, group_id: int) -> Project:
    """Создает тестовый проект в БД."""
    project = Project(
        name=f"Test Project {random_string(5)}",
        description="Test project for tasks",
        group_id=group_id
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@pytest.mark.asyncio
async def test_create_task(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует создание задачи."""
    # Создаем пользователя, группу и проект
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)
    project = await create_test_project(db_session, group.id)

    headers = await get_async_auth_headers(async_client, user.email, "testpassword")

    # Устанавливаем deadline в будущем
    deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    task_data = {
        "title": f"Test Task {random_string(5)}",
        "description": "Test task description",
        "status": TaskStatus.NEW.value,
        "priority": TaskPriority.MEDIUM.value,
        "project_id": project.id,
        "deadline": deadline
    }

    response = await async_client.post("/api/v1/tasks/", json=task_data, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["status"] == TaskStatus.NEW.value


@pytest.mark.asyncio
async def test_change_task_status(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует изменение статуса задачи."""
    # Создаем пользователя, группу и проект
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)
    project = await create_test_project(db_session, group.id)

    headers = await get_async_auth_headers(async_client, user.email, "testpassword")

    # Создаем задачу
    deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    task_data = {
        "title": f"Status Test Task {random_string(5)}",
        "description": "Task for testing status changes",
        "status": TaskStatus.NEW.value,
        "priority": TaskPriority.MEDIUM.value,
        "project_id": project.id,
        "deadline": deadline
    }

    task_response = await async_client.post("/api/v1/tasks/", json=task_data, headers=headers)
    task_id = task_response.json()["id"]

    # Меняем статус задачи
    new_status = TaskStatus.IN_PROGRESS.value
    status_response = await async_client.patch(
        f"/api/v1/tasks/{task_id}/status?status={new_status}",
        headers=headers
    )

    assert status_response.status_code == 200
    assert status_response.json()["status"] == new_status


@pytest.mark.asyncio
async def test_add_comment_to_task(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Тестирует добавление комментария к задаче."""
    # Создаем пользователя, группу и проект
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)
    project = await create_test_project(db_session, group.id)

    headers = await get_async_auth_headers(async_client, user.email, "testpassword")

    # Создаем задачу
    task_data = {
        "title": f"Comment Test Task {random_string(5)}",
        "description": "Task for testing comments",
        "status": TaskStatus.NEW.value,
        "priority": TaskPriority.MEDIUM.value,
        "project_id": project.id
    }

    task_response = await async_client.post("/api/v1/tasks/", json=task_data, headers=headers)
    task_id = task_response.json()["id"]

    # Добавляем комментарий
    comment_data = {
        "content": f"Test comment {random_string(10)}"
    }

    comment_response = await async_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json=comment_data,
        headers=headers
    )

    assert comment_response.status_code == 200
    assert comment_response.json()["content"] == comment_data["content"]