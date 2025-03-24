from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from src.models.project import Project

async def get_project_by_id(db: AsyncSession, id: int) -> Optional[Project]:
    result = await db.execute(select(Project).where(Project.id == id))
    return result.scalars().first()

async def get_all_projects(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Project]:
    result = await db.execute(select(Project).offset(skip).limit(limit))
    return result.scalars().all()

async def get_projects_by_group(db: AsyncSession, group_id: int, skip: int = 0, limit: int = 100) -> List[Project]:
    result = await db.execute(
        select(Project).where(Project.group_id == group_id).offset(skip).limit(limit)
    )
    return result.scalars().all()

async def create_project_in_db(db: AsyncSession, project: Project) -> None:
    db.add(project)
    await db.commit()
    await db.refresh(project)

async def update_project_in_db(db: AsyncSession, project: Project) -> None:
    db.add(project)
    await db.commit()
    await db.refresh(project)

async def delete_project_from_db(db: AsyncSession, id: int) -> bool:
    result = await db.execute(delete(Project).where(Project.id == id))
    await db.commit()
    return result.rowcount > 0