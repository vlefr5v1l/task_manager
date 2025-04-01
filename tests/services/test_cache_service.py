"""
Tests for the Redis cache integration.
Tests caching functionality with mocked Redis.
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any

import pytest
from pydantic import BaseModel

from src.cache.client import get_cache, set_cache, delete_cache, invalidate_pattern
from src.models.project import Project
from src.services import project as project_service


# Example Pydantic model for testing
class TestModel(BaseModel):
    id: int
    name: str
    created_at: datetime


@pytest.mark.asyncio
async def test_get_cache_hit(mock_redis):
    """Test successfully retrieving data from cache."""
    # Arrange
    key = "test-key"
    expected_data = {"id": 1, "name": "Test Data"}

    # Seed the cache
    await mock_redis.set(key, expected_data)

    # Act
    result = await get_cache(key)

    # Assert
    assert result == expected_data


@pytest.mark.asyncio
async def test_get_cache_miss(mock_redis):
    """Test cache miss returns None."""
    # Arrange
    key = "non-existent-key"

    # Act
    result = await get_cache(key)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_set_cache(mock_redis):
    """Test setting data in cache."""
    # Arrange
    key = "new-key"
    data = {"id": 2, "name": "New Data"}

    # Act
    result = await set_cache(key, data, expires=60)

    # Assert
    assert result is True
    cached_data = await mock_redis.get(key)
    assert cached_data == data
    assert mock_redis.ttls[key] == 60


@pytest.mark.asyncio
async def test_delete_cache(mock_redis):
    """Test deleting data from cache."""
    # Arrange
    key = "delete-key"
    data = {"id": 3, "name": "Delete Me"}

    # Seed the cache
    await mock_redis.set(key, data)

    # Act
    result = await delete_cache(key)

    # Assert
    assert result is True
    cached_data = await mock_redis.get(key)
    assert cached_data is None


@pytest.mark.asyncio
async def test_invalidate_pattern(mock_redis):
    """Test invalidating multiple cache keys by pattern."""
    # Arrange
    # Seed multiple cache entries with different prefixes
    await mock_redis.set("project:1", {"id": 1, "name": "Project 1"})
    await mock_redis.set("project:2", {"id": 2, "name": "Project 2"})
    await mock_redis.set("user:1", {"id": 1, "name": "User 1"})

    # Act
    count = await invalidate_pattern("project:*")

    # Assert
    assert count == 2
    assert await mock_redis.get("project:1") is None
    assert await mock_redis.get("project:2") is None
    assert await mock_redis.get("user:1") is not None


@pytest.mark.asyncio
async def test_cache_complex_object(mock_redis):
    """Test caching complex objects with nested structures."""
    # Arrange
    key = "complex:1"
    now = datetime.now(timezone.utc)
    model = TestModel(id=1, name="Complex Object", created_at=now)

    # Act
    # Serialize model to dict for caching
    await set_cache(key, model.model_dump())
    cached_data = await get_cache(key)

    # Assert
    assert cached_data is not None
    # Create model from cached data
    recreated_model = TestModel(**cached_data)
    assert recreated_model.id == model.id
    assert recreated_model.name == model.name
    # Convert string back to datetime for comparison
    assert recreated_model.created_at.replace(microsecond=0) == model.created_at.replace(microsecond=0)


@pytest.mark.asyncio
async def test_project_service_caching(mock_session, mock_redis):
    """Test project service cache functionality with mock Redis."""
    # Arrange
    project_id = 1
    project_data = {
        "id": project_id,
        "name": "Cached Project",
        "description": "This project should be cached",
        "group_id": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Set up mock project in cache
    cache_key = f"project:{project_id}"
    await mock_redis.set(cache_key, project_data)

    # Act
    # This should use the cached data without hitting the database
    from unittest.mock import patch
    with patch('src.repo.project.get_project_by_id') as mock_repo_get:
        # Call service method
        project = await project_service.get(mock_session, project_id)

        # Assert
        # Repository should not be called because data is in cache
        mock_repo_get.assert_not_called()

        # Project should match our cached data
        assert project is not None
        assert project.id == project_id
        assert project.name == project_data["name"]
        assert project.description == project_data["description"]


@pytest.mark.asyncio
async def test_cache_invalidation_on_update(mock_session, mock_redis):
    """Test cache invalidation when updating a project."""
    # Arrange
    project_id = 2
    project = Project(
        id=project_id,
        name="Original Name",
        description="Original description",
        group_id=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Put original project in cache
    cache_key = f"project:{project_id}"
    await mock_redis.set(
        cache_key,
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "group_id": project.group_id,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }
    )

    # Mock project update via repository
    from unittest.mock import patch, AsyncMock
    with patch('src.repo.project.update_project_in_db', new_callable=AsyncMock) as mock_update:
        # Create update data
        from src.schemas.project import ProjectUpdate
        update_data = ProjectUpdate(name="Updated Name")

        # Call service method to update project
        await project_service.update(mock_session, db_obj=project, obj_in=update_data)

        # Assert
        # Update should have been called
        mock_update.assert_called_once()

        # Cache should be invalidated
        assert await mock_redis.get(cache_key) is None

        # Other cache invalidation patterns should be called
        assert "projects:list:" in [key for key in mock_redis.cache.keys()]