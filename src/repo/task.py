from typing import List, Optional, Dict, Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.task import Task, Comment
from src.models.user import User


async def get_task_by_id(db: AsyncSession, id: int) -> Optional[Task]:
    """Получает задачу по идентификатору"""
    result = await db.execute(select(Task).where(Task.id == id))
    return result.scalars().first()


async def get_tasks_with_filters(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Task]:
    """Получает список задач с применением фильтров"""
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


async def create_task_in_db(db: AsyncSession, task: Task) -> None:
    """Создает задачу в базе данных"""
    db.add(task)
    await db.commit()
    await db.refresh(task)


async def update_task_in_db(db: AsyncSession, task: Task) -> None:
    """Обновляет задачу в базе данных"""
    db.add(task)
    await db.commit()
    await db.refresh(task)


async def delete_task_from_db(db: AsyncSession, id: int) -> bool:
    """Удаляет задачу из базы данных"""
    result = await db.execute(delete(Task).where(Task.id == id))
    await db.commit()
    return result.rowcount > 0


async def get_user_by_id(db: AsyncSession, id: int) -> Optional[User]:
    """Получает пользователя по идентификатору"""
    result = await db.execute(select(User).where(User.id == id))
    return result.scalars().first()


# Функции для работы с комментариями
async def create_comment_in_db(db: AsyncSession, comment: Comment) -> None:
    """Создает комментарий в базе данных"""
    db.add(comment)
    await db.commit()
    await db.refresh(comment)


async def get_comments_by_task_id(db: AsyncSession, task_id: int) -> List[Comment]:
    """Получает комментарии к задаче"""
    result = await db.execute(select(Comment).where(Comment.task_id == task_id).order_by(Comment.created_at))
    return result.scalars().all()


async def delete_comment_from_db(db: AsyncSession, comment_id: int) -> bool:
    """Удаляет комментарий из базы данных"""
    result = await db.execute(delete(Comment).where(Comment.id == comment_id))
    await db.commit()
    return result.rowcount > 0
