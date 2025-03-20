from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from src.models.group import Group, GroupMember, GroupRole
from src.models.user import User
from src.schemas.group import GroupCreate, GroupUpdate


async def get(db: AsyncSession, id: int) -> Optional[Group]:
    result = await db.execute(select(Group).where(Group.id == id))
    return result.scalars().first()


async def get_by_name(db: AsyncSession, name: str) -> Optional[Group]:
    result = await db.execute(select(Group).where(Group.name == name))
    return result.scalars().first()


async def get_multi(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Group]:
    result = await db.execute(select(Group).offset(skip).limit(limit))
    return result.scalars().all()


async def create(db: AsyncSession, *, obj_in: GroupCreate) -> Group:
    db_obj = Group(
        name=obj_in.name,
        description=obj_in.description
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update(db: AsyncSession, *, db_obj: Group, obj_in: GroupUpdate) -> Group:
    obj_data = obj_in.dict(exclude_unset=True)

    for field, value in obj_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, *, id: int) -> bool:
    result = await db.execute(delete(Group).where(Group.id == id))
    await db.commit()
    return result.rowcount > 0


# Функции для управления членами группы
async def add_user_to_group(db: AsyncSession, *, group_id: int, user_id: int,
                            role: GroupRole = GroupRole.DEVELOPER) -> GroupMember:
    db_obj = GroupMember(
        group_id=group_id,
        user_id=user_id,
        role=role
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def remove_user_from_group(db: AsyncSession, *, group_id: int, user_id: int) -> bool:
    result = await db.execute(
        delete(GroupMember).where(
            (GroupMember.group_id == group_id) & (GroupMember.user_id == user_id)
        )
    )
    await db.commit()
    return result.rowcount > 0


async def update_user_role(db: AsyncSession, *, group_id: int, user_id: int, role: GroupRole) -> Optional[GroupMember]:
    result = await db.execute(
        update(GroupMember)
        .where((GroupMember.group_id == group_id) & (GroupMember.user_id == user_id))
        .values(role=role)
        .returning(GroupMember)
    )
    await db.commit()
    return result.scalars().first()


async def get_group_members(db: AsyncSession, *, group_id: int) -> List[GroupMember]:
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    return result.scalars().all()


async def is_user_in_group(db: AsyncSession, *, group_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(GroupMember).where(
            (GroupMember.group_id == group_id) & (GroupMember.user_id == user_id)
        )
    )
    return result.scalars().first() is not None


async def get_user_role_in_group(db: AsyncSession, *, group_id: int, user_id: int) -> Optional[GroupRole]:
    result = await db.execute(
        select(GroupMember.role).where(
            (GroupMember.group_id == group_id) & (GroupMember.user_id == user_id)
        )
    )
    member = result.scalars().first()
    return member