from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update

from src.models.project import Project
from src.schemas.project import ProjectCreate, ProjectUpdate


async def get(db: AsyncSession, id: int) -> Optional[Project]:
    result = await db.execute(select(Project).where(Project.id == id))
    return result.scalars().first()


async def get_multi(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Project]:
    result = await db.execute(select(Project).offset(skip).limit(limit))
    return result.scalars().all()


async def get_by_group(db: AsyncSession, group_id: int, skip: int = 0, limit: int = 100) -> List[Project]:
    result = await db.execute(select(Project).where(Project.group_id == group_id).offset(skip).limit(limit))
    return result.scalars().all()


async def create(db: AsyncSession, *, obj_in: ProjectCreate) -> Project:
    db_obj = Project(name=obj_in.name, description=obj_in.description, group_id=obj_in.group_id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update(db: AsyncSession, *, db_obj: Project, obj_in: ProjectUpdate) -> Project:
    obj_data = obj_in.dict(exclude_unset=True)

    for field, value in obj_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, *, id: int) -> bool:
    result = await db.execute(delete(Project).where(Project.id == id))
    await db.commit()
    return result.rowcount > 0
