"""
Test utility functions and fixtures.
Provides helper functions and fixtures for creating test data.
"""
import random
import string
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserRole
from src.models.task import Task, TaskStatus, TaskPriority
from src.models.project import Project
from src.models.group import Group, GroupMember, GroupRole
from src.validator.security import get_password_hash, create_access_token


def random_string(length: int = 10) -> str:
    """Generate a random string for test data."""
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    """Generate a random email for test data."""
    return f"{random_string(8)}@{random_string(6)}.com"


def random_date(
        start_date: datetime = datetime.now(timezone.utc) - timedelta(days=30),
        end_date: datetime = datetime.now(timezone.utc)
) -> datetime:
    """Generate a random date between start_date and end_date."""
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)


async def create_test_user(
        db: AsyncSession,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: str = "testpassword",
        role: UserRole = UserRole.DEVELOPER,
        is_active: bool = True,
) -> User:
    """Create a test user in the database."""
    if username is None:
        username = random_string()
    if email is None:
        email = random_email()

    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_test_group(
        db: AsyncSession,
        name: Optional[str] = None,
        description: str = "Test group description",
) -> Group:
    """Create a test group in the database."""
    if name is None:
        name = f"Test Group {random_string(5)}"

    group = Group(
        name=name,
        description=description,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def add_user_to_group(
        db: AsyncSession,
        user_id: int,
        group_id: int,
        role: GroupRole = GroupRole.DEVELOPER,
) -> GroupMember:
    """Add a user to a group with the specified role."""
    group_member = GroupMember(
        user_id=user_id,
        group_id=group_id,
        role=role,
    )
    db.add(group_member)
    await db.commit()
    await db.refresh(group_member)
    return group_member


async def create_test_project(
        db: AsyncSession,
        name: Optional[str] = None,
        description: str = "Test project description",
        group_id: Optional[int] = None,
) -> Project:
    """Create a test project in the database."""
    if name is None:
        name = f"Test Project {random_string(5)}"

    project = Project(
        name=name,
        description=description,
        group_id=group_id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def create_test_task(
        db: AsyncSession,
        title: Optional[str] = None,
        description: str = "Test task description",
        status: TaskStatus = TaskStatus.NEW,
        priority: TaskPriority = TaskPriority.MEDIUM,
        created_by_id: int = None,
        assigned_to_id: Optional[int] = None,
        project_id: int = None,
        deadline: Optional[datetime] = None,
) -> Task:
    """Create a test task in the database."""
    if title is None:
        title = f"Test Task {random_string(5)}"
    if deadline is None:
        deadline = datetime.now(timezone.utc) + timedelta(days=7)

    task = Task(
        title=title,
        description=description,
        status=status,
        priority=priority,
        created_by_id=created_by_id,
        assigned_to_id=assigned_to_id,
        project_id=project_id,
        deadline=deadline,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_auth_token_headers(
        client: TestClient,
        email: str,
        password: str
) -> Dict[str, str]:
    """
    Get authentication token headers by logging in.
    Returns a dictionary with the Authorization header.
    """
    login_data = {
        "username": email,
        "password": password,
    }
    response = await client.post("/api/v1/auth/login", data=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def get_direct_auth_headers(user_id: int) -> Dict[str, str]:
    """
    Create authentication headers directly without logging in.
    Useful for tests where we don't want to go through the login process.
    """
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def assert_task_equals(task_data: Dict[str, Any], expected: Dict[str, Any]) -> None:
    """
    Assert that a task response data matches expected values.
    Only checks the fields present in expected dictionary.
    """
    for key, value in expected.items():
        if key in task_data:
            assert task_data[key] == value, f"Field '{key}' mismatch: got {task_data[key]}, expected {value}"


def assert_user_equals(user_data: Dict[str, Any], expected: Dict[str, Any]) -> None:
    """
    Assert that a user response data matches expected values.
    Only checks the fields present in expected dictionary.
    """
    for key, value in expected.items():
        if key in user_data:
            assert user_data[key] == value, f"Field '{key}' mismatch: got {user_data[key]}, expected {value}"