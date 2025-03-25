import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from src.core.config import settings

# URL тестовой базы данных
TEST_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
TEST_DB_NAME = "test_task_management"


async def setup_test_db():
    """Создает тестовую базу данных и применяет миграции"""
    print(f"Setting up test database: {TEST_DB_NAME}")

    # Подключаемся к основной базе postgres
    engine = create_async_engine(TEST_DATABASE_URL)

    try:
        # Проверяем существование тестовой базы
        async with engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
            )
            db_exists = result.scalar_one_or_none()

            # Если база не существует, создаем её
            if not db_exists:
                # Завершаем транзакцию перед созданием БД
                await conn.execute(text("COMMIT"))
                print(f"Creating database {TEST_DB_NAME}...")
                await conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
                print(f"Database {TEST_DB_NAME} created successfully")
            else:
                print(f"Database {TEST_DB_NAME} already exists")

        # Применяем миграции к тестовой базе
        print("Applying migrations to test database...")
        os.system(f"alembic upgrade head")
        print("Migrations applied successfully")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(setup_test_db())