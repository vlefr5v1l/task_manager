"""
Parameterized API tests using the test utilities.
Demonstrates how to use the parameterized testing utilities.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from src.models.user import UserRole
from src.models.group import GroupRole
from src.models.task import TaskStatus, TaskPriority
from tests.utils.test_utils import (
    create_test_user,
    create_test_group,
    add_user_to_group,
    create_test_project,
    create_test_task,
    get_auth_token_headers,
    random_string
)
from tests.utils.parameterized import (
    api_test_cases,
    permission_test_cases,
    task_api_test_cases,
    get_task_test_data
)


@pytest.mark.asyncio
@api_test_cases(task_api_test_cases())
async def test_task_api_endpoints(
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_case: dict,
        mock_kafka
):
    """Test task API endpoints with parameterized data."""
    # Set up prerequisites - create test user, group, project
    user = await create_test_user(db_session, role=UserRole.ADMIN)
    group = await create_test_group(db_session)
    await add_user_to_group(db_session, user.id, group.id, GroupRole.TEAM_LEAD)
    project = await create_test_project(db_session, group_id=group.id)

    # Update project_id in test data to use the actual project ID
    if "data" in test_case and "project_id" in test_case["data"]:
        test_case["data"]["project_id"] = project.id

    # Get authentication headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # Get the method function from the client
    method_func = getattr(async_client, test_case["method"])

    # Make the request
    response = await method_func(
        test_case["endpoint"],
        json=test_case.get("data"),
        headers=headers
    )

    # Check status code
    assert response.status_code == test_case["expected_status"], \
        f"Expected status {test_case['expected_status']} but got {response.status_code}: {response.text}"

    # Check response data if expected and successful
    if "expected_response" in test_case and response.status_code < 400:
        response_data = response.json()
        for key, value in test_case["expected_response"].items():
            assert response_data[key] == value, \
                f"Expected {key}={value} but got {key}={response_data.get(key)}"


@pytest.mark.asyncio
@permission_test_cases(
    endpoint="/api/v1/projects/",
    method="post",
    allowed_combinations=[
        (UserRole.ADMIN, None),
        (UserRole.TEAM_LEAD, GroupRole.TEAM_LEAD),
        (UserRole.DEVELOPER, GroupRole.TEAM_LEAD),
        (UserRole.OBSERVER, GroupRole.TEAM_LEAD)
    ]
)
async def test_project_creation_permissions(
        async_client: AsyncClient,
        db_session: AsyncSession,
        permission_case: dict
):
    """Test permissions for project creation with different role combinations."""
    # Create a user with the specified role
    user = await create_test_user(db_session, role=permission_case["user_role"])

    # Create a group if needed
    group = None
    if permission_case["group_role"] is not None:
        group = await create_test_group(db_session)
        # Add user to the group with specified role
        await add_user_to_group(
            db_session,
            user.id,
            group.id,
            permission_case["group_role"]
        )

    # Get authentication headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # Prepare project data
    project_data = {
        "name": f"Test Project {random_string(5)}",
        "description": "Test project description",
        "group_id": group.id if group else 1  # Use 1 as a fallback
    }

    # Get the method function from the client
    method_func = getattr(async_client, permission_case["method"])

    # Make the request
    response = await method_func(
        permission_case["endpoint"],
        json=project_data,
        headers=headers
    )

    # Check status code
    assert response.status_code == permission_case["expected_status"], \
        f"Expected status {permission_case['expected_status']} but got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_task_status_changes(
        async_client: AsyncClient,
        db_session: AsyncSession
):
    """Test changing task status with different role combinations."""
    # Define test cases for status transitions
    status_transitions = [
        # (from_status, to_status, user_role, expected_success)
        (TaskStatus.NEW, TaskStatus.IN_PROGRESS, UserRole.DEVELOPER, True),
        (TaskStatus.IN_PROGRESS, TaskStatus.WAITING, UserRole.DEVELOPER, True),
        (TaskStatus.WAITING, TaskStatus.IN_PROGRESS, UserRole.DEVELOPER, True),
        (TaskStatus.IN_PROGRESS, TaskStatus.RESOLVED, UserRole.DEVELOPER, True),
        # TODO
        # (TaskStatus.RESOLVED, TaskStatus.CLOSED, UserRole.DEVELOPER, False),  # Only creator can close
        # (TaskStatus.RESOLVED, TaskStatus.CLOSED, UserRole.TEAM_LEAD, True),  # Team lead can close
    ]

    # Test each transition
    for from_status, to_status, user_role, expected_success in status_transitions:
        # Create creator and assignee
        creator = await create_test_user(db_session, role=UserRole.TEAM_LEAD)
        assignee = await create_test_user(db_session, role=user_role)

        # Create group and project
        group = await create_test_group(db_session)
        await add_user_to_group(db_session, creator.id, group.id, GroupRole.TEAM_LEAD)
        await add_user_to_group(db_session, assignee.id, group.id, GroupRole.DEVELOPER)
        project = await create_test_project(db_session, group_id=group.id)

        # Create task with initial status
        task = await create_test_task(
            db_session,
            title=f"Task for {from_status.value} to {to_status.value}",
            status=from_status,
            created_by_id=creator.id,
            assigned_to_id=assignee.id,
            project_id=project.id
        )

        # Get assignee's auth headers
        headers = await get_auth_token_headers(async_client, assignee.email, "testpassword")

        # Try to change status
        response = await async_client.patch(
            f"/api/v1/tasks/{task.id}/status?status={to_status.value}",
            headers=headers
        )

        # Check if result matches expectation
        expected_status = status.HTTP_200_OK if expected_success else status.HTTP_403_FORBIDDEN
        assert response.status_code == expected_status, \
            f"Transition {from_status.value}->{to_status.value} with {user_role.value}: " \
            f"Expected {expected_status}, got {response.status_code}"

        # If successful, verify status was changed
        if expected_success:
            assert response.json()["status"] == to_status.value, \
                f"Status not changed correctly: {response.json()['status']} != {to_status.value}"


@pytest.mark.asyncio
async def test_filter_combinations(
        async_client: AsyncClient,
        db_session: AsyncSession
):
    """Test various filter combinations for the tasks endpoint."""
    # Create test user and get auth
    user = await create_test_user(db_session, role=UserRole.ADMIN)
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    # Create test project
    group = await create_test_group(db_session)
    project = await create_test_project(db_session, group_id=group.id)

    # Create tasks with different properties
    # 1. High priority, new
    await create_test_task(
        db_session,
        title="High Priority Task",
        status=TaskStatus.NEW,
        priority=TaskPriority.HIGH,
        created_by_id=user.id,
        project_id=project.id
    )

    # 2. High priority, in progress
    await create_test_task(
        db_session,
        title="High Priority In Progress Task",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        created_by_id=user.id,
        project_id=project.id
    )

    # 3. Medium priority, new
    await create_test_task(
        db_session,
        title="Medium Priority New Task",
        status=TaskStatus.NEW,
        priority=TaskPriority.MEDIUM,
        created_by_id=user.id,
        project_id=project.id
    )

    # Define filter combinations to test
    filter_tests = [
        {
            "name": "filter_by_high_priority",
            "query_params": {"priority": TaskPriority.HIGH.value},
            "expected_count": 2,
            "title_contains": "High Priority"
        },
        {
            "name": "filter_by_new_status",
            "query_params": {"status": TaskStatus.NEW.value},
            "expected_count": 2,
            "title_contains": "Task"
        },
        {
            "name": "filter_by_high_priority_and_new_status",
            "query_params": {
                "priority": TaskPriority.HIGH.value,
                "status": TaskStatus.NEW.value
            },
            "expected_count": 1,
            "title_contains": "High Priority Task"
        },
        {
            "name": "filter_by_project",
            "query_params": {"project_id": project.id},
            "expected_count": 3
        },
        {
            "name": "filter_by_creator",
            "query_params": {"created_by_id": user.id},
            "expected_count": 3
        }
    ]

    # Test each filter combination
    for test in filter_tests:
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in test["query_params"].items()])

        # Make request
        response = await async_client.get(
            f"/api/v1/tasks/?{query_string}",
            headers=headers
        )

        # Check status and count
        assert response.status_code == status.HTTP_200_OK, \
            f"Filter test '{test['name']}' failed with status {response.status_code}"

        tasks = response.json()
        assert len(tasks) >= test["expected_count"], \
            f"Filter test '{test['name']}' expected at least {test['expected_count']} tasks, got {len(tasks)}"

        # Check title if specified
        if "title_contains" in test:
            for task in tasks:
                assert test["title_contains"] in task["title"], \
                    f"Task title '{task['title']}' doesn't contain '{test['title_contains']}'"