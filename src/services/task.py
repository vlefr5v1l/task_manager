from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from src.models.task import Task, Comment, TaskStatus, TaskPriority
from src.schemas.task import TaskCreate, TaskUpdate, CommentCreate
from src.messaging.producers import send_event
import src.repo.task as task_repo
import logging

log = logging.getLogger(__name__)


def get_utc_now():
    return datetime.now(timezone.utc)


async def get(db: AsyncSession, id: int) -> Optional[Task]:
    return await task_repo.get_task_by_id(db, id)


async def get_multi(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Task]:
    return await task_repo.get_tasks_with_filters(db, skip, limit, filters)


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

    await task_repo.create_task_in_db(db, db_obj)

    # Получаем email пользователя, если задача назначена
    assigned_to_email = None
    if db_obj.assigned_to_id:
        user = await task_repo.get_user_by_id(db, db_obj.assigned_to_id)
        if user:
            assigned_to_email = user.email

    # Отправляем событие в Kafka
    await send_event(
        topic="task_events",
        event_type="task_created",
        data={
            "id": db_obj.id,
            "title": db_obj.title,
            "description": db_obj.description,
            "status": db_obj.status.value,
            "priority": db_obj.priority.value,
            "created_by_id": created_by_id,
            "assigned_to_id": db_obj.assigned_to_id,
            "assigned_to_email": assigned_to_email,
            "project_id": db_obj.project_id,
        },
    )

    return db_obj


async def update(db: AsyncSession, *, db_obj: Task, obj_in: TaskUpdate) -> Task:
    obj_data = obj_in.dict(exclude_unset=True)

    # Обработка deadline, если он задан
    if "deadline" in obj_data and obj_data["deadline"] is not None:
        deadline = obj_data["deadline"]
        if deadline.tzinfo is None:
            log.debug(f"Converting naive datetime to UTC: {obj_data['deadline']}")
            obj_data["deadline"] = deadline.replace(tzinfo=timezone.utc)

    # Обновляем атрибуты объекта
    for field, value in obj_data.items():
        setattr(db_obj, field, value)

    # Обновляем время изменения
    db_obj.updated_at = get_utc_now()

    # Сохраняем в БД
    await task_repo.update_task_in_db(db, db_obj)

    # Получаем email пользователя, если задача назначена
    assigned_to_email = None
    if db_obj.assigned_to_id:
        user = await task_repo.get_user_by_id(db, db_obj.assigned_to_id)
        if user:
            assigned_to_email = user.email

    # Отправляем событие в Kafka
    await send_event(
        topic="task_events",
        event_type="task_updated",
        data={
            "id": db_obj.id,
            "title": db_obj.title,
            "description": db_obj.description,
            "status": db_obj.status.value,
            "priority": db_obj.priority.value,
            "assigned_to_id": db_obj.assigned_to_id,
            "assigned_to_email": assigned_to_email,
            "project_id": db_obj.project_id,
        },
    )

    return db_obj


async def delete(db: AsyncSession, *, id: int) -> bool:
    return await task_repo.delete_task_from_db(db, id)


async def change_status(db: AsyncSession, *, task_id: int, status: TaskStatus) -> Optional[Task]:
    task = await task_repo.get_task_by_id(db, task_id)
    if not task:
        return None

    task.status = status
    task.updated_at = get_utc_now()

    await task_repo.update_task_in_db(db, task)
    return task


# Функции для комментариев
async def create_comment(db: AsyncSession, *, task_id: int, user_id: int, obj_in: CommentCreate) -> Comment:
    db_obj = Comment(task_id=task_id, user_id=user_id, content=obj_in.content)
    await task_repo.create_comment_in_db(db, db_obj)

    # Здесь можно также отправить событие в Kafka
    return db_obj


async def get_task_comments(db: AsyncSession, *, task_id: int) -> List[Comment]:
    return await task_repo.get_comments_by_task_id(db, task_id)


async def delete_comment(db: AsyncSession, *, comment_id: int) -> bool:
    return await task_repo.delete_comment_from_db(db, comment_id)
