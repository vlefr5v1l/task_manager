import asyncio
import pytest
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import asyncpg

from src.main import app
from src.db.base import Base
from src.db.session import get_db
from src.core.config import settings

# Тестовая БД
TEST_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/test_task_management"

# Создаем тестовый движок
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


# Переопределяем зависимость для получения БД
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


# Устанавливаем тестовую зависимость
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Создает экземпляр цикла событий для каждой тестовой сессии.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """
    Создает тестовую БД и таблицы, после тестов удаляет их.
    """
    # Подключаемся к PostgreSQL и создаем тестовую БД если её нет
    postgres_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"

    # Проверяем, существует ли база данных
    try:
        # Подключаемся к основной БД postgres
        conn = await asyncpg.connect(postgres_url)

        # Проверяем существование тестовой БД
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            "test_task_management"
        )

        # Если БД не существует, создаем её
        if not db_exists:
            await conn.execute("CREATE DATABASE test_task_management")

        await conn.close()
    except Exception as e:
        pytest.fail(f"Failed to create test database: {e}")

    # Создаем таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Запускаем тесты
    yield

    # Удаляем таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Возвращает сессию БД для каждого теста и делает откат изменений после теста.
    """
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def client(test_db) -> Generator:
    """
    Создает тестовый клиент для запросов к API.
    """
    with TestClient(app) as c:
        yield c