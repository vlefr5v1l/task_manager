from typing import List, Optional

from sqlalchemy import update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.group import Group, GroupMember, GroupRole


async def get_group_by_id(db: AsyncSession, id: int) -> Optional[Group]:
    """Получает группу по идентификатору"""
    result = await db.execute(select(Group).where(Group.id == id))
    return result.scalars().first()


async def get_group_by_name(db: AsyncSession, name: str) -> Optional[Group]:
    """Получает группу по имени"""
    result = await db.execute(select(Group).where(Group.name == name))
    return result.scalars().first()


async def get_all_groups(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Group]:
    """Получает список всех групп с пагинацией"""
    result = await db.execute(select(Group).offset(skip).limit(limit))
    return result.scalars().all()


async def create_group_in_db(db: AsyncSession, group: Group) -> None:
    """Создает группу в базе данных"""
    db.add(group)
    await db.commit()
    await db.refresh(group)


async def update_group_in_db(db: AsyncSession, group: Group) -> None:
    """Обновляет группу в базе данных"""
    db.add(group)
    await db.commit()
    await db.refresh(group)


async def delete_group_from_db(db: AsyncSession, id: int) -> bool:
    """Удаляет группу из базы данных"""
    result = await db.execute(delete(Group).where(Group.id == id))
    await db.commit()
    return result.rowcount > 0


# Репозиторий для членов группы
async def create_group_member_in_db(db: AsyncSession, group_member: GroupMember) -> None:
    """Создает членство в группе"""
    db.add(group_member)
    await db.commit()
    await db.refresh(group_member)


async def delete_group_member_from_db(db: AsyncSession, group_id: int, user_id: int) -> bool:
    """Удаляет пользователя из группы"""
    result = await db.execute(
        delete(GroupMember).where((GroupMember.group_id == group_id) & (GroupMember.user_id == user_id))
    )
    await db.commit()
    return result.rowcount > 0


async def update_member_role_in_db(
    db: AsyncSession, group_id: int, user_id: int, role: GroupRole
) -> Optional[GroupMember]:
    """Обновляет роль пользователя в группе"""
    result = await db.execute(
        update(GroupMember)
        .where((GroupMember.group_id == group_id) & (GroupMember.user_id == user_id))
        .values(role=role)
        .returning(GroupMember)
    )
    await db.commit()
    return result.scalars().first()


async def get_members_by_group_id(db: AsyncSession, group_id: int) -> List[GroupMember]:
    """Получает всех участников группы"""
    result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id))
    return result.scalars().all()


async def get_group_member(db: AsyncSession, group_id: int, user_id: int) -> Optional[GroupMember]:
    """Получает запись о членстве в группе"""
    result = await db.execute(
        select(GroupMember).where((GroupMember.group_id == group_id) & (GroupMember.user_id == user_id))
    )
    return result.scalars().first()


async def get_member_role(db: AsyncSession, group_id: int, user_id: int) -> Optional[GroupRole]:
    """Получает роль пользователя в группе"""
    result = await db.execute(
        select(GroupMember.role).where((GroupMember.group_id == group_id) & (GroupMember.user_id == user_id))
    )
    return result.scalars().first()
