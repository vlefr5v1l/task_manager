from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from src.db.session import get_db
from src.api.v1.endpoints.auth import get_current_user
from src.models.user import User, UserRole
from src.models.group import GroupRole
from src.models.task import TaskStatus, TaskPriority
from src.schemas.task import (
    Task,
    TaskCreate,
    TaskUpdate,
    Comment,
    CommentCreate,
    TaskWithComments,
)
from src.services import task as task_service
from src.services import project as project_service
from src.services import group as group_service

router = APIRouter()


# Проверка прав на проект
async def check_project_access(db: AsyncSession, project_id: int, current_user: User) -> bool:
    # Администратор имеет доступ ко всем проектам
    if current_user.role == UserRole.ADMIN:
        return True

    # Получаем проект
    project = await project_service.get(db=db, id=project_id)
    if not project:
        return False

    # Проверяем, является ли пользователь участником группы проекта
    return await group_service.is_user_in_group(db=db, group_id=project.group_id, user_id=current_user.id)


# Проверка прав на задачу
async def check_task_access(db: AsyncSession, task_id: int, current_user: User) -> Task:
    # Получаем задачу
    task = await task_service.get(db=db, id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача с ID {task_id} не найдена",
        )

    # Администратор имеет доступ ко всем задачам
    if current_user.role == UserRole.ADMIN:
        return task

    # Проверяем доступ к проекту
    if not await check_project_access(db=db, project_id=task.project_id, current_user=current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой задаче",
        )

    return task


# Проверка прав на редактирование задачи
async def check_task_edit_rights(db: AsyncSession, task: Task, current_user: User) -> None:
    # Администратор имеет полные права
    if current_user.role == UserRole.ADMIN:
        return

    # Получаем проект
    project = await project_service.get(db=db, id=task.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Проект задачи не найден")

    # Тимлид группы имеет полные права на редактирование
    role = await group_service.get_user_role_in_group(db=db, group_id=project.group_id, user_id=current_user.id)
    if role == GroupRole.TEAM_LEAD:
        return

    # Создатель задачи имеет права на редактирование
    if task.created_by_id == current_user.id:
        return

    # Назначенный исполнитель имеет право менять статус задачи
    if task.assigned_to_id == current_user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="У вас недостаточно прав для редактирования этой задачи",
    )


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    *,
    db: AsyncSession = Depends(get_db),
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Создать новую задачу.
    """
    # Проверяем доступ к проекту
    if not await check_project_access(db=db, project_id=task_in.project_id, current_user=current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому проекту",
        )

    # Создаем задачу
    task = await task_service.create(db=db, obj_in=task_in, created_by_id=current_user.id)
    return task


@router.get("/", response_model=List[Task])
async def read_tasks(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    created_by_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    deadline_from: Optional[datetime] = None,
    deadline_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Получить список задач с фильтрацией.
    """
    filters = {
        "project_id": project_id,
        "status": status,
        "priority": priority,
        "created_by_id": created_by_id,
        "assigned_to_id": assigned_to_id,
        "deadline_from": deadline_from,
        "deadline_to": deadline_to,
    }

    # Если указан проект, проверяем доступ к нему
    if project_id is not None and not await check_project_access(
        db=db, project_id=project_id, current_user=current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому проекту",
        )

    tasks = await task_service.get_multi(db=db, skip=skip, limit=limit, filters=filters)

    # Если пользователь не админ, фильтруем только задачи из доступных проектов
    if current_user.role != UserRole.ADMIN and project_id is None:
        filtered_tasks = []
        for task in tasks:
            if await check_project_access(db=db, project_id=task.project_id, current_user=current_user):
                filtered_tasks.append(task)
        return filtered_tasks

    return tasks


@router.get("/{task_id}", response_model=TaskWithComments)
async def read_task(
    *,
    db: AsyncSession = Depends(get_db),
    task_id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Получить информацию о конкретной задаче по ID, включая комментарии.
    """
    task = await check_task_access(db=db, task_id=task_id, current_user=current_user)

    # Получаем комментарии к задаче
    comments = await task_service.get_task_comments(db=db, task_id=task_id)

    # Создаем объект TaskWithComments
    task_with_comments = TaskWithComments.from_orm(task)
    task_with_comments.comments = comments

    return task_with_comments


@router.put("/{task_id}", response_model=Task)
async def update_task(
    *,
    db: AsyncSession = Depends(get_db),
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Обновить информацию о задаче.
    """
    task = await check_task_access(db=db, task_id=task_id, current_user=current_user)

    # Проверяем права на редактирование
    await check_task_edit_rights(db=db, task=task, current_user=current_user)

    # Если меняется проект, проверяем доступ к новому проекту
    if task_in.project_id and task_in.project_id != task.project_id:
        if not await check_project_access(db=db, project_id=task_in.project_id, current_user=current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет доступа к этому проекту",
            )

    updated_task = await task_service.update(db=db, db_obj=task, obj_in=task_in)
    return updated_task


@router.patch("/{task_id}/status", response_model=Task)
async def update_task_status(
    *,
    db: AsyncSession = Depends(get_db),
    task_id: int,
    status: TaskStatus,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Обновить статус задачи.
    """
    task = await check_task_access(db=db, task_id=task_id, current_user=current_user)

    # Проверяем права на изменение статуса
    # Тимлид группы и администратор могут менять любой статус
    if current_user.role != UserRole.ADMIN:
        project = await project_service.get(db=db, id=task.project_id)
        role = await group_service.get_user_role_in_group(db=db, group_id=project.group_id, user_id=current_user.id)

        # Если не тимлид, проверяем дополнительные условия
        if role != GroupRole.TEAM_LEAD:
            # Проверяем, является ли пользователь создателем или исполнителем
            if task.created_by_id != current_user.id and task.assigned_to_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="У вас нет прав менять статус этой задачи",
                )

            # Проверяем переходы между статусами
            if (
                task.status == TaskStatus.RESOLVED
                and status != TaskStatus.CLOSED
                and task.created_by_id != current_user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Только создатель задачи может переводить её из статуса RESOLVED в другой статус",
                )

    updated_task = await task_service.change_status(db=db, task_id=task_id, status=status)
    return updated_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    *,
    db: AsyncSession = Depends(get_db),
    task_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Удалить задачу.
    """
    task = await check_task_access(db=db, task_id=task_id, current_user=current_user)

    # Проверка, может ли пользователь удалить задачу
    if current_user.role != UserRole.ADMIN:
        project = await project_service.get(db=db, id=task.project_id)
        role = await group_service.get_user_role_in_group(db=db, group_id=project.group_id, user_id=current_user.id)

        # Только тимлид или создатель задачи может её удалить
        if role != GroupRole.TEAM_LEAD and task.created_by_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет прав удалить эту задачу",
            )

    await task_service.delete(db=db, id=task_id)


# Эндпоинты для комментариев
@router.post("/{task_id}/comments", response_model=Comment)
async def create_task_comment(
    *,
    db: AsyncSession = Depends(get_db),
    task_id: int,
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Добавить комментарий к задаче.
    """
    # Проверяем доступ к задаче
    await check_task_access(db=db, task_id=task_id, current_user=current_user)

    # Создаем комментарий
    comment = await task_service.create_comment(db=db, task_id=task_id, user_id=current_user.id, obj_in=comment_in)

    return comment


@router.get("/{task_id}/comments", response_model=List[Comment])
async def read_task_comments(
    *,
    db: AsyncSession = Depends(get_db),
    task_id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Получить все комментарии к задаче.
    """
    # Проверяем доступ к задаче
    await check_task_access(db=db, task_id=task_id, current_user=current_user)

    comments = await task_service.get_task_comments(db=db, task_id=task_id)
    return comments


@router.delete("/{task_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_comment(
    *,
    db: AsyncSession = Depends(get_db),
    task_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Удалить комментарий к задаче.
    """
    # Проверяем доступ к задаче
    task = await check_task_access(db=db, task_id=task_id, current_user=current_user)

    # Получаем комментарий
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalars().first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Комментарий с ID {comment_id} не найден",
        )

    # Проверяем, что комментарий принадлежит указанной задаче
    if comment.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Комментарий не принадлежит указанной задаче",
        )

    # Проверяем права на удаление комментария
    if current_user.role != UserRole.ADMIN and comment.user_id != current_user.id:
        # Проверяем, является ли пользователь тимлидом
        project = await project_service.get(db=db, id=task.project_id)
        role = await group_service.get_user_role_in_group(db=db, group_id=project.group_id, user_id=current_user.id)

        if role != GroupRole.TEAM_LEAD:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете удалять только свои комментарии",
            )

    await task_service.delete_comment(db=db, comment_id=comment_id)
