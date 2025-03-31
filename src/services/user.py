from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

import src.repo.user as user_repo
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate
from src.validator.security import get_password_hash, verify_password


async def get(db: AsyncSession, id: int) -> Optional[User]:
    """Получает пользователя по идентификатору"""
    return await user_repo.get_user_by_id(db, id)


async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Получает пользователя по email"""
    return await user_repo.get_user_by_email(db, email)


async def get_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Получает пользователя по имени пользователя"""
    return await user_repo.get_user_by_username(db, username)


async def create(db: AsyncSession, *, obj_in: UserCreate) -> User:
    """Создает нового пользователя"""
    # Создаем объект пользователя с хэшированным паролем
    db_obj = User(
        username=obj_in.username,
        email=obj_in.email,
        password_hash=get_password_hash(obj_in.password),
        full_name=obj_in.full_name,
        role=obj_in.role,
    )

    # Сохраняем в базу данных
    await user_repo.create_user_in_db(db, db_obj)

    return db_obj


async def get_multi(db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[User]:
    """Получает список пользователей с пагинацией"""
    return await user_repo.get_all_users(db, skip, limit)


async def update(db: AsyncSession, *, db_obj: User, obj_in: UserUpdate) -> User:
    """Обновляет информацию о пользователе"""
    # Обрабатываем входные данные
    obj_data = obj_in.dict(exclude_unset=True)

    # Хэшируем пароль, если он присутствует
    if obj_data.get("password"):
        obj_data["password_hash"] = get_password_hash(obj_data.pop("password"))

    # Обновляем атрибуты пользователя
    for field, value in obj_data.items():
        setattr(db_obj, field, value)

    # Сохраняем изменения в базе данных
    await user_repo.update_user_in_db(db, db_obj)

    return db_obj


async def authenticate(db: AsyncSession, *, username_or_email: str, password: str) -> Optional[User]:
    """
    Проверяет пользователя по username или email и паролю
    """
    # Пробуем найти пользователя по email
    user = await get_by_email(db, email=username_or_email)

    # Если пользователь не найден по email, ищем по username
    if not user:
        user = await get_by_username(db, username=username_or_email)

    # Проверяем пароль, если пользователь найден
    if not user or not verify_password(password, user.password_hash):
        return None

    return user
