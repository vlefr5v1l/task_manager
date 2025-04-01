"""
Unit tests for the task service.
Tests task service functions with mocked dependencies.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.task import Task, TaskStatus, TaskPriority, Comment
from src.models.user import User
from src.schemas.task import TaskCreate, TaskUpdate, CommentCreate
from src.services import task as task_service
from tests.mocks.services import mock_execute_with_first_result, mock_execute_with_all_results


# Helper for creating a test task model
def create_test_task_model(
    id: int = 1,
    title: str = "Test Task",
    status: TaskStatus = TaskStatus.NEW,
    priority: TaskPriority = TaskPriority.MEDIUM,
    created_by_id: int = 1,
    assigned_to_id: int = 2,
    project_id: int = 1,
) -> Task:
    """Create a Task model instance for testing."""
    now = datetime.now(timezone.utc)
    return Task(
        id=id,
        title=title,
        description="Test description",
        status=status,
        priority=priority,
        created_by_id=created_by_id,
        assigned_to_id=assigned_to_id,
        project_id=project_id,
        deadline=now + timedelta(days=7),
        created_at=now,
        updated_at=now
    )


# Helper for creating a test user model
def create_test_user_model(
    id: int = 1,
    username: str = "testuser",
    email: str = "test@example.com"
) -> User:
    """Create a User model instance for testing."""
    return User(
        id=id,
        username=username,
        email=email,
        password_hash="hashed_password",
        is_active=True
    )


@pytest.mark.asyncio
async def test_get_task_by_id(mock_session):
    """Test retrieving a task by ID."""
    # Arrange
    task_id = 1
    expected_task = create_test_task_model(id=task_id)
    await mock_execute_with_first_result(mock_session, expected_task)

    # Act
    result = await task_service.get(mock_session, task_id)

    # Assert
    assert result == expected_task
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_task_by_id_not_found(mock_session):
    """Test retrieving a non-existent task by ID."""
    # Arrange
    task_id = 999
    await mock_execute_with_first_result(mock_session, None)

    # Act
    result = await task_service.get(mock_session, task_id)

    # Assert
    assert result is None
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_multi_with_filters(mock_session):
    """Test retrieving multiple tasks with filters."""
    # Arrange
    expected_tasks = [
        create_test_task_model(id=1),
        create_test_task_model(id=2, title="Another Task")
    ]
    await mock_execute_with_all_results(mock_session, expected_tasks)

    filters = {
        "project_id": 1,
        "status": TaskStatus.NEW
    }

    # Act
    result = await task_service.get_multi(mock_session, skip=0, limit=10, filters=filters)

    # Assert
    assert result == expected_tasks
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_task(mock_session, mock_kafka):
    """Test creating a new task."""
    # Arrange
    task_create = TaskCreate(
        title="New Task",
        description="New task description",
        project_id=1,
        priority=TaskPriority.HIGH
    )

    # Mock the create_task_in_db function
    with patch('src.repo.task.create_task_in_db', new_callable=AsyncMock) as mock_create:
        # Mock get_user_by_id to return a user
        with patch('src.repo.task.get_user_by_id', new_callable=AsyncMock) as mock_get_user:
            user = create_test_user_model(id=2)
            mock_get_user.return_value = user

            # Act
            created_task = await task_service.create(
                db=mock_session,
                obj_in=task_create,
                created_by_id=1
            )

            # Assert
            assert created_task is not None
            assert created_task.title == task_create.title
            assert created_task.created_by_id == 1
            mock_create.assert_called_once()

            # Check Kafka event
            assert len(mock_kafka.sent_messages) == 1
            event = mock_kafka.sent_messages[0]
            assert event["topic"] == "task_events"
            assert event["message"]["event_type"] == "task_created"


@pytest.mark.asyncio
async def test_update_task(mock_session, mock_kafka):
    """Test updating an existing task."""
    # Arrange
    task_id = 1
    existing_task = create_test_task_model(id=task_id)

    task_update = TaskUpdate(
        title="Updated Task",
        status=TaskStatus.IN_PROGRESS
    )

    # Mock update_task_in_db
    with patch('src.repo.task.update_task_in_db', new_callable=AsyncMock) as mock_update:
        # Mock get_user_by_id to return a user
        with patch('src.repo.task.get_user_by_id', new_callable=AsyncMock) as mock_get_user:
            user = create_test_user_model(id=2)
            mock_get_user.return_value = user

            # Act
            updated_task = await task_service.update(
                db=mock_session,
                db_obj=existing_task,
                obj_in=task_update
            )

            # Assert
            assert updated_task is not None
            assert updated_task.title == "Updated Task"
            assert updated_task.status == TaskStatus.IN_PROGRESS
            mock_update.assert_called_once()

            # Check Kafka event
            assert len(mock_kafka.sent_messages) == 1
            event = mock_kafka.sent_messages[0]
            assert event["topic"] == "task_events"
            assert event["message"]["event_type"] == "task_updated"


@pytest.mark.asyncio
async def test_delete_task(mock_session):
    """Test deleting a task."""
    # Arrange
    task_id = 1

    # Mock delete_task_from_db to return True (successful deletion)
    with patch('src.repo.task.delete_task_from_db', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = True

        # Act
        result = await task_service.delete(db=mock_session, id=task_id)

        # Assert
        assert result is True
        mock_delete.assert_called_once_with(mock_session, task_id)


@pytest.mark.asyncio
async def test_change_task_status(mock_session):
    """Test changing the status of a task."""
    # Arrange
    task_id = 1
    new_status = TaskStatus.IN_PROGRESS

    # Mock get_task_by_id to return a task
    with patch('src.repo.task.get_task_by_id', new_callable=AsyncMock) as mock_get_task:
        task = create_test_task_model(id=task_id)
        mock_get_task.return_value = task

        # Mock update_task_in_db
        with patch('src.repo.task.update_task_in_db', new_callable=AsyncMock) as mock_update:
            # Act
            updated_task = await task_service.change_status(
                db=mock_session,
                task_id=task_id,
                status=new_status
            )

            # Assert
            assert updated_task is not None
            assert updated_task.status == new_status
            mock_get_task.assert_called_once_with(mock_session, task_id)
            mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_create_comment(mock_session):
    """Test creating a comment for a task."""
    # Arrange
    task_id = 1
    user_id = 2
    comment_create = CommentCreate(content="Test comment")

    # Mock create_comment_in_db
    with patch('src.repo.task.create_comment_in_db', new_callable=AsyncMock) as mock_create:
        # Set up the mock to add an id to the comment
        async def add_id_to_comment(db, comment):
            comment.id = 1
            comment.created_at = datetime.now(timezone.utc)
            return comment

        mock_create.side_effect = add_id_to_comment

        # Act
        created_comment = await task_service.create_comment(
            db=mock_session,
            task_id=task_id,
            user_id=user_id,
            obj_in=comment_create
        )

        # Assert
        assert created_comment is not None
        assert created_comment.content == "Test comment"
        assert created_comment.task_id == task_id
        assert created_comment.user_id == user_id
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_get_task_comments(mock_session):
    """Test retrieving comments for a task."""
    # Arrange
    task_id = 1
    expected_comments = [
        Comment(id=1, task_id=task_id, user_id=2, content="First comment", created_at=datetime.now(timezone.utc)),
        Comment(id=2, task_id=task_id, user_id=3, content="Second comment", created_at=datetime.now(timezone.utc))
    ]

    # Mock get_comments_by_task_id
    with patch('src.repo.task.get_comments_by_task_id', new_callable=AsyncMock) as mock_get_comments:
        mock_get_comments.return_value = expected_comments

        # Act
        comments = await task_service.get_task_comments(db=mock_session, task_id=task_id)

        # Assert
        assert comments == expected_comments
        mock_get_comments.assert_called_once_with(mock_session, task_id)


@pytest.mark.asyncio
async def test_delete_comment(mock_session):
    """Test deleting a comment."""
    # Arrange
    comment_id = 1

    # Mock delete_comment_from_db to return True (successful deletion)
    with patch('src.repo.task.delete_comment_from_db', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = True

        # Act
        result = await task_service.delete_comment(db=mock_session, comment_id=comment_id)

        # Assert
        assert result is True
        mock_delete.assert_called_once_with(mock_session, comment_id)


@pytest.mark.asyncio
async def test_get_task_with_timezone_aware_dates():
    """Test that task service correctly handles timezone-aware dates."""
    # Arrange
    mock_db = AsyncMock(spec=AsyncSession)
    task_create = TaskCreate(
        title="Timezone Test Task",
        description="Testing timezone handling",
        project_id=1,
        deadline=datetime.now()  # Naive datetime
    )

    # Mock create_task_in_db
    with patch('src.repo.task.create_task_in_db', new_callable=AsyncMock) as mock_create:
        with patch('src.repo.task.get_user_by_id', new_callable=AsyncMock) as mock_get_user:
            # Mock user
            mock_get_user.return_value = create_test_user_model()

            # Act
            created_task = await task_service.create(
                db=mock_db,
                obj_in=task_create,
                created_by_id=1
            )

            # Assert
            assert created_task.deadline is not None
            # Ensure deadline is timezone aware
            assert created_task.deadline.tzinfo is not None
            # Ensure created_at is timezone aware
            assert created_task.created_at.tzinfo is not None
            # Ensure updated_at is timezone aware
            assert created_task.updated_at.tzinfo is not None