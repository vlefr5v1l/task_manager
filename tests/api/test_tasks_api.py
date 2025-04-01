"""
Integration tests for the tasks API.
Tests the tasks API endpoints with a test database.
"""
import json
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient

from src.models.task import TaskStatus, TaskPriority
from src.models.user import UserRole
from src.models.group import GroupRole
from sqlalchemy.ext.asyncio import AsyncSession

from tests.mocks.services import patch_kafka
from tests.utils.test_utils import (
    create_test_user,
    create_test_group,
    add_user_to_group,
    create_test_project,
    create_test_task,
    get_auth_token_headers,
    random_string
)


@pytest.mark.asyncio
async def test_create_task(async_client: AsyncClient, db_session: AsyncSession, mock_kafka):
    """Test creating a task through the API."""
    # Arrange - Create test data

    user = await create_test_user(db_session, role=UserRole.DEVELOPER)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id, GroupRole.DEVELOPER)
    project = await create_test_project(db_session, group_id=group.id)

    # Get authentication headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # Create task data
    task_data = {
        "title": f"API Test Task {random_string(5)}",
        "description": "Task created through API test",
        "status": TaskStatus.NEW.value,
        "priority": TaskPriority.MEDIUM.value,
        "project_id": project.id,
        "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    }

    # Act - Send request to create task
    response = await async_client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=headers
    )

    # Assert - Check response
    assert response.status_code == 201
    response_data = response.json()

    # Verify task was created correctly
    assert response_data["title"] == task_data["title"]
    assert response_data["description"] == task_data["description"]
    assert response_data["status"] == task_data["status"]
    assert response_data["priority"] == task_data["priority"]
    assert response_data["project_id"] == task_data["project_id"]
    assert response_data["created_by_id"] == user.id

    # Verify Kafka event was sent
    assert len(mock_kafka.sent_messages) > 0
    event = mock_kafka.sent_messages[0]
    assert event["topic"] == "task_events"
    assert event["message"]["event_type"] == "task_created"
    assert event["message"]["data"]["title"] == task_data["title"]


@pytest.mark.asyncio
async def test_get_tasks_with_filters(async_client: AsyncClient, db_session: AsyncSession):
    """Test retrieving tasks with filters."""
    # Arrange - Create test data
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)
    project = await create_test_project(db_session, group_id=group.id)

    # Create multiple tasks with different properties
    await create_test_task(
        db_session,
        title="High Priority Task",
        priority=TaskPriority.HIGH,
        created_by_id=user.id,
        project_id=project.id
    )
    await create_test_task(
        db_session,
        title="Medium Priority Task",
        priority=TaskPriority.MEDIUM,
        created_by_id=user.id,
        project_id=project.id
    )
    await create_test_task(
        db_session,
        title="Low Priority Task",
        priority=TaskPriority.LOW,
        created_by_id=user.id,
        project_id=project.id
    )

    # Get authentication headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # Act - Get tasks with filter for high priority
    response = await async_client.get(
        f"/api/v1/tasks/?priority={TaskPriority.HIGH.value}&project_id={project.id}",
        headers=headers
    )

    # Assert - Check response
    assert response.status_code == 200
    tasks = response.json()

    # Should only have high priority tasks
    assert len(tasks) >= 1
    for task in tasks:
        assert task["priority"] == TaskPriority.HIGH.value
        assert task["project_id"] == project.id


@pytest.mark.asyncio
async def test_update_task(async_client: AsyncClient, db_session: AsyncSession, mock_kafka):
    """Test updating a task through the API."""
    # Arrange - Create test data
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)
    project = await create_test_project(db_session, group_id=group.id)

    # Create a task
    task = await create_test_task(
        db_session,
        title="Task to Update",
        status=TaskStatus.NEW,
        created_by_id=user.id,
        project_id=project.id
    )

    # Get authentication headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # Update data
    update_data = {
        "title": "Updated Task Title",
        "status": TaskStatus.IN_PROGRESS.value
    }

    # Clear Kafka messages before this test
    mock_kafka.clear()

    # Act - Send request to update task
    response = await async_client.put(
        f"/api/v1/tasks/{task.id}",
        json=update_data,
        headers=headers
    )

    # Assert - Check response
    assert response.status_code == 200
    response_data = response.json()

    # Verify task was updated correctly
    assert response_data["title"] == update_data["title"]
    assert response_data["status"] == update_data["status"]

    # Verify Kafka event was sent
    assert len(mock_kafka.sent_messages) > 0
    event = mock_kafka.sent_messages[0]
    assert event["topic"] == "task_events"
    assert event["message"]["event_type"] == "task_updated"


@pytest.mark.asyncio
async def test_change_task_status(async_client: AsyncClient, db_session: AsyncSession):
    """Test changing the status of a task."""
    # Arrange - Create test data
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)
    project = await create_test_project(db_session, group_id=group.id)

    # Create a task
    task = await create_test_task(
        db_session,
        title="Task for Status Change",
        status=TaskStatus.NEW,
        created_by_id=user.id,
        project_id=project.id
    )

    # Get authentication headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # New status
    new_status = TaskStatus.IN_PROGRESS

    # Act - Send request to change status
    response = await async_client.patch(
        f"/api/v1/tasks/{task.id}/status?status={new_status.value}",
        headers=headers
    )

    # Assert - Check response
    assert response.status_code == 200
    response_data = response.json()

    # Verify status was changed correctly
    assert response_data["status"] == new_status.value


@pytest.mark.asyncio
async def test_add_comment_to_task(async_client: AsyncClient, db_session: AsyncSession):
    """Test adding a comment to a task."""
    # Arrange - Create test data
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)
    project = await create_test_project(db_session, group_id=group.id)

    # Create a task
    task = await create_test_task(
        db_session,
        title="Task for Comment",
        created_by_id=user.id,
        project_id=project.id
    )

    # Get authentication headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # Comment data
    comment_data = {
        "content": f"Test comment {random_string(10)}"
    }

    # Act - Send request to add comment
    response = await async_client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json=comment_data,
        headers=headers
    )

    # Assert - Check response
    assert response.status_code == 200
    response_data = response.json()

    # Verify comment was added correctly
    assert response_data["content"] == comment_data["content"]
    assert response_data["task_id"] == task.id
    assert response_data["user_id"] == user.id


@pytest.mark.asyncio
async def test_get_task_with_comments(async_client: AsyncClient, db_session: AsyncSession):
    """Test retrieving a task with its comments."""
    # Arrange - Create test data
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)
    project = await create_test_project(db_session, group_id=group.id)

    # Create a task
    task = await create_test_task(
        db_session,
        title="Task with Comments",
        created_by_id=user.id,
        project_id=project.id
    )

    # Get authentication headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # Add comments
    comment_text_1 = f"First comment {random_string(5)}"
    comment_text_2 = f"Second comment {random_string(5)}"

    # Add first comment
    await async_client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": comment_text_1},
        headers=headers
    )

    # Add second comment
    await async_client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": comment_text_2},
        headers=headers
    )

    # Act - Get task with comments
    response = await async_client.get(
        f"/api/v1/tasks/{task.id}",
        headers=headers
    )

    # Assert - Check response
    assert response.status_code == 200
    response_data = response.json()

    # Verify task data is correct
    assert response_data["id"] == task.id
    assert response_data["title"] == task.title

    # Verify comments are included
    assert "comments" in response_data
    assert len(response_data["comments"]) == 2
    comment_contents = [c["content"] for c in response_data["comments"]]
    assert comment_text_1 in comment_contents
    assert comment_text_2 in comment_contents


@pytest.mark.asyncio
async def test_delete_task(async_client: AsyncClient, db_session: AsyncSession):
    """Test deleting a task."""
    # Arrange - Create test data
    user = await create_test_user(db_session)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id)
    project = await create_test_project(db_session, group_id=group.id)

    # Create a task
    task = await create_test_task(
        db_session,
        title="Task to Delete",
        created_by_id=user.id,
        project_id=project.id
    )

    # Get authentication headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # Act - Send request to delete task
    response = await async_client.delete(
        f"/api/v1/tasks/{task.id}",
        headers=headers
    )

    # Assert - Check response
    assert response.status_code == 204

    # Verify task was deleted by trying to get it
    get_response = await async_client.get(
        f"/api/v1/tasks/{task.id}",
        headers=headers
    )

    # Should get 404 Not Found
    assert get_response.status_code == 404