"""
Enhanced pytest configuration file.
Provides fixtures for testing with mocks for external services.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator, Dict, Any

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from src.core.config import settings
from src.db.base import Base
from src.db.session import get_db
from src.main import app
from tests.mocks.services import (
    patch_redis, patch_kafka, mock_db_session,
    MockRepository, MockRedisCache, MockKafkaProducer
)
from src.models.user import User
from src.models.task import Task
from src.models.project import Project
from src.models.group import Group

# Test database URL
TEST_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/test_task_management"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
    future=True,
    poolclass=NullPool,
)
TestingSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# Override database dependency
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Apply the dependency override
app.dependency_overrides[get_db] = override_get_db


# Event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    """Create a new event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Database fixtures
@pytest_asyncio.fixture(scope="session")
async def test_db():
    """Create test database tables for the test session."""
    # Connect to postgres to create test database if it doesn't exist
    postgres_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"

    # Connect to default postgres database
    try:
        conn = await asyncpg.connect(postgres_url)

        # Check if test database exists
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", "test_task_management")

        # Create test database if it doesn't exist
        if not db_exists:
            await conn.execute("CREATE DATABASE test_task_management")
            print("Test database created successfully")

        await conn.close()
    except Exception as e:
        print(f"Error creating test database: {e}")
        raise

    # Now create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Drop tables after tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for each test with rollback after."""
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# Mock service fixtures
@pytest.fixture
def mock_redis() -> Generator[MockRedisCache, None, None]:
    """Provide a mock Redis cache and patch the Redis functions."""
    mock_redis_instance, patches = patch_redis()

    # Start patches
    for patch_item in patches:
        patch_item.start()

    yield mock_redis_instance

    # Stop patches
    for patch_item in patches:
        patch_item.stop()


@pytest.fixture
def mock_kafka() -> Generator[MockKafkaProducer, None, None]:
    """Provide a mock Kafka producer and patch the Kafka functions."""
    mock_kafka_instance, patches = patch_kafka()

    # Start patches
    for patch_item in patches:
        patch_item.start()

    yield mock_kafka_instance

    # Stop patches
    for patch_item in patches:
        patch_item.stop()


@pytest.fixture
def mock_session() -> AsyncSession:
    """Provide a mock database session for unit tests."""
    return mock_db_session()


# Repository fixtures
@pytest.fixture
def mock_user_repo() -> MockRepository:
    """Provide a mock user repository for unit tests."""
    return MockRepository[User, int](User)


@pytest.fixture
def mock_task_repo() -> MockRepository:
    """Provide a mock task repository for unit tests."""
    return MockRepository[Task, int](Task)


@pytest.fixture
def mock_project_repo() -> MockRepository:
    """Provide a mock project repository for unit tests."""
    return MockRepository[Project, int](Project)


@pytest.fixture
def mock_group_repo() -> MockRepository:
    """Provide a mock group repository for unit tests."""
    return MockRepository[Group, int](Group)


# HTTP client fixture
@pytest_asyncio.fixture
async def async_client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# Test environment configuration
@pytest.fixture(autouse=True)
def set_test_env():
    """Set environment to testing."""
    os.environ["TESTING"] = "1"
    yield
    os.environ.pop("TESTING", None)


# Combined fixtures for common testing scenarios
@pytest_asyncio.fixture
async def authenticated_client(
        async_client, db_session
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Provide an authenticated client with a test user.
    Returns a dictionary with the client, user, and auth headers.
    """
    from tests.utils.test_utils import create_test_user, get_auth_token_headers

    # Create test user
    user = await create_test_user(db_session)

    # Get auth headers
    headers = await get_auth_token_headers(async_client, user.email, "testpassword")

    yield {
        "client": async_client,
        "user": user,
        "headers": headers
    }