from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

import src.repo.group as group_repo
from src.models.group import Group, GroupMember, GroupRole
from src.schemas.group import GroupCreate, GroupUpdate


async def get(db: AsyncSession, id: int) -> Optional[Group]:
    """Получает группу по идентификатору"""
    return await group_repo.get_group_by_id(db, id)


async def get_by_name(db: AsyncSession, name: str) -> Optional[Group]:
    """Получает группу по имени"""
    return await group_repo.get_group_by_name(db, name)


async def get_multi(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Group]:
    """Получает список всех групп с пагинацией"""
    return await group_repo.get_all_groups(db, skip, limit)


async def create(db: AsyncSession, *, obj_in: GroupCreate) -> Group:
    """Создает новую группу"""
    # Создаем объект группы
    db_obj = Group(name=obj_in.name, description=obj_in.description)

    # Сохраняем в базу данных
    await group_repo.create_group_in_db(db, db_obj)

    return db_obj


async def update(db: AsyncSession, *, db_obj: Group, obj_in: GroupUpdate) -> Group:
    """Обновляет информацию о группе"""
    # Обновляем атрибуты объекта
    obj_data = obj_in.dict(exclude_unset=True)
    for field, value in obj_data.items():
        setattr(db_obj, field, value)

    # Сохраняем изменения в базе данных
    await group_repo.update_group_in_db(db, db_obj)

    return db_obj


async def delete(db: AsyncSession, *, id: int) -> bool:
    """Удаляет группу"""
    return await group_repo.delete_group_from_db(db, id)


# Функции для управления членами группы
async def add_user_to_group(
    db: AsyncSession,
    *,
    group_id: int,
    user_id: int,
    role: GroupRole = GroupRole.DEVELOPER,
) -> GroupMember:
    """Добавляет пользователя в группу"""
    # Создаем объект членства в группе
    db_obj = GroupMember(group_id=group_id, user_id=user_id, role=role)

    # Сохраняем в базу данных
    await group_repo.create_group_member_in_db(db, db_obj)

    return db_obj


async def remove_user_from_group(db: AsyncSession, *, group_id: int, user_id: int) -> bool:
    """Удаляет пользователя из группы"""
    return await group_repo.delete_group_member_from_db(db, group_id, user_id)


async def update_user_role(db: AsyncSession, *, group_id: int, user_id: int, role: GroupRole) -> Optional[GroupMember]:
    """Обновляет роль пользователя в группе"""
    return await group_repo.update_member_role_in_db(db, group_id, user_id, role)


async def get_group_members(db: AsyncSession, *, group_id: int) -> List[GroupMember]:
    """Получает список всех участников группы"""
    return await group_repo.get_members_by_group_id(db, group_id)


async def is_user_in_group(db: AsyncSession, *, group_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь участником группы"""
    member = await group_repo.get_group_member(db, group_id, user_id)
    return member is not None


async def get_user_role_in_group(db: AsyncSession, *, group_id: int, user_id: int) -> Optional[GroupRole]:
    """Получает роль пользователя в группе"""
    return await group_repo.get_member_role(db, group_id, user_id)
