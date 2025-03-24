from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.user import User


async def get_user_by_id(db: AsyncSession, id: int) -> Optional[User]:
    """Получает пользователя по идентификатору"""
    result = await db.execute(select(User).where(User.id == id))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Получает пользователя по email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Получает пользователя по имени пользователя"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def create_user_in_db(db: AsyncSession, user: User) -> None:
    """Создает пользователя в базе данных"""
    db.add(user)
    await db.commit()
    await db.refresh(user)


async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Получает список всех пользователей с пагинацией"""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def update_user_in_db(db: AsyncSession, user: User) -> None:
    """Обновляет пользователя в базе данных"""
    db.add(user)
    await db.commit()
    await db.refresh(user)