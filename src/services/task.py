from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update, and_, or_
from datetime import datetime, timezone

from src.models.task import Task, Comment, TaskStatus, TaskPriority
from src.schemas.task import TaskCreate, TaskUpdate, CommentCreate


def get_utc_now():
    return datetime.now(timezone.utc)


async def get(db: AsyncSession, id: int) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == id))
    return result.scalars().first()


async def get_multi(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Task]:
    query = select(Task)

    # Применяем фильтры, если они указаны
    if filters:
        if "project_id" in filters and filters["project_id"] is not None:
            query = query.where(Task.project_id == filters["project_id"])
        if "status" in filters and filters["status"] is not None:
            query = query.where(Task.status == filters["status"])
        if "priority" in filters and filters["priority"] is not None:
            query = query.where(Task.priority == filters["priority"])
        if "created_by_id" in filters and filters["created_by_id"] is not None:
            query = query.where(Task.created_by_id == filters["created_by_id"])
        if "assigned_to_id" in filters and filters["assigned_to_id"] is not None:
            query = query.where(Task.assigned_to_id == filters["assigned_to_id"])
        if "deadline_from" in filters and filters["deadline_from"] is not None:
            query = query.where(Task.deadline >= filters["deadline_from"])
        if "deadline_to" in filters and filters["deadline_to"] is not None:
            query = query.where(Task.deadline <= filters["deadline_to"])

    # Добавляем пагинацию
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def create(db: AsyncSession, *, obj_in: TaskCreate, created_by_id: int) -> Task:
    # Преобразуем deadline в timezone-aware, если он задан
    deadline = obj_in.deadline
    if deadline and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    # Используем timezone-aware datetime для created_at и updated_at
    now = get_utc_now()

    db_obj = Task(
        title=obj_in.title,
        description=obj_in.description,
        status=obj_in.status,
        priority=obj_in.priority,
        created_by_id=created_by_id,
        assigned_to_id=obj_in.assigned_to_id,
        project_id=obj_in.project_id,
        deadline=deadline,
        created_at=now,
        updated_at=now,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update(db: AsyncSession, *, db_obj: Task, obj_in: TaskUpdate) -> Task:
    obj_data = obj_in.dict(exclude_unset=True)

    # Обработка deadline, если он задан
    if "deadline" in obj_data and obj_data["deadline"] is not None:
        deadline = obj_data["deadline"]
        if deadline.tzinfo is None:
            obj_data["deadline"] = deadline.replace(tzinfo=timezone.utc)

    for field, value in obj_data.items():
        setattr(db_obj, field, value)

    # Обновляем время изменения
    db_obj.updated_at = get_utc_now()

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, *, id: int) -> bool:
    result = await db.execute(delete(Task).where(Task.id == id))
    await db.commit()
    return result.rowcount > 0


async def change_status(db: AsyncSession, *, task_id: int, status: TaskStatus) -> Optional[Task]:
    task = await get(db, id=task_id)
    if not task:
        return None

    task.status = status
    task.updated_at = datetime.utcnow()

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


# Функции для комментариев
async def create_comment(db: AsyncSession, *, task_id: int, user_id: int, obj_in: CommentCreate) -> Comment:
    db_obj = Comment(task_id=task_id, user_id=user_id, content=obj_in.content)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_task_comments(db: AsyncSession, *, task_id: int) -> List[Comment]:
    result = await db.execute(select(Comment).where(Comment.task_id == task_id).order_by(Comment.created_at))
    return result.scalars().all()


async def delete_comment(db: AsyncSession, *, comment_id: int) -> bool:
    result = await db.execute(delete(Comment).where(Comment.id == comment_id))
    await db.commit()
    return result.rowcount > 0
