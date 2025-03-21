from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.api.v1.endpoints.auth import get_current_user
from src.models.user import User, UserRole
from src.models.group import GroupRole
from src.schemas.project import Project, ProjectCreate, ProjectUpdate
from src.services import project as project_service
from src.services import group as group_service

router = APIRouter()


async def check_project_rights(
    db: AsyncSession, project_id: int, current_user: User
) -> Project:
    project = await project_service.get(db=db, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Проект с ID {project_id} не найден",
        )

    if current_user.role == UserRole.ADMIN:
        return project

    if not await group_service.is_user_in_group(
        db=db, group_id=project.group_id, user_id=current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому проекту",
        )

    return project


async def check_project_edit_rights(
    db: AsyncSession, project_id: int, current_user: User
) -> Project:
    project = await check_project_rights(
        db=db, project_id=project_id, current_user=current_user
    )

    if current_user.role != UserRole.ADMIN:
        role = await group_service.get_user_role_in_group(
            db=db, group_id=project.group_id, user_id=current_user.id
        )
        if role != GroupRole.TEAM_LEAD:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас недостаточно прав для редактирования проекта",
            )

    return project


@router.post("/", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Создать новый проект.
    """
    # Проверяем существование группы
    group = await group_service.get(db=db, id=project_in.group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с ID {project_in.group_id} не найдена",
        )

    if current_user.role != UserRole.ADMIN:
        role = await group_service.get_user_role_in_group(
            db=db, group_id=project_in.group_id, user_id=current_user.id
        )
        if not role or role != GroupRole.TEAM_LEAD:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для создания проекта в этой группе",
            )

    project = await project_service.create(db=db, obj_in=project_in)
    return project


@router.get("/", response_model=List[Project])
async def read_projects(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    group_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Получить список проектов.
    Можно фильтровать по group_id.
    """
    if group_id:
        # Проверяем существование группы
        group = await group_service.get(db=db, id=group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Группа с ID {group_id} не найдена",
            )

        # Проверяем права доступа к группе (кроме админа)
        if current_user.role != UserRole.ADMIN:
            if not await group_service.is_user_in_group(
                db=db, group_id=group_id, user_id=current_user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="У вас нет доступа к этой группе",
                )

        projects = await project_service.get_by_group(
            db=db, group_id=group_id, skip=skip, limit=limit
        )
    else:
        # Для админа показываем все проекты
        if current_user.role == UserRole.ADMIN:
            projects = await project_service.get_multi(db=db, skip=skip, limit=limit)
        else:
            # Для обычного пользователя показываем только проекты из его групп
            # Здесь нужна более сложная логика с присоединением таблиц
            projects = await project_service.get_multi(db=db, skip=skip, limit=limit)
            # TODO: Фильтровать проекты только по группам пользователя

    return projects


@router.get("/{project_id}", response_model=Project)
async def read_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Получить информацию о конкретном проекте по ID.
    """
    project = await check_project_rights(
        db=db, project_id=project_id, current_user=current_user
    )
    return project


@router.put("/{project_id}", response_model=Project)
async def update_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: int,
    project_in: ProjectUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Обновить информацию о проекте.
    """
    project = await check_project_edit_rights(
        db=db, project_id=project_id, current_user=current_user
    )

    if project_in.group_id and project_in.group_id != project.group_id:
        if current_user.role != UserRole.ADMIN:
            role = await group_service.get_user_role_in_group(
                db=db, group_id=project_in.group_id, user_id=current_user.id
            )
            if not role or role != GroupRole.TEAM_LEAD:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав для перемещения проекта в эту группу",
                )

    updated_project = await project_service.update(
        db=db, db_obj=project, obj_in=project_in
    )
    return updated_project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Удалить проект.
    """
    await check_project_edit_rights(
        db=db, project_id=project_id, current_user=current_user
    )
    await project_service.delete(db=db, id=project_id)
