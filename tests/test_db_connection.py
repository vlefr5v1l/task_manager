import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_SERVER"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            port=os.getenv("POSTGRES_PORT"),
        )
        print("Успешное подключение к PostgreSQL через asyncpg!")
        await conn.close()
    except Exception as e:
        print(f"Ошибка подключения: {e}")

asyncio.run(test_connection())