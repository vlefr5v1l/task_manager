from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.api.v1.endpoints.auth import get_current_user
from src.models.user import User, UserRole
from src.models.group import GroupRole
from src.schemas.group import (
    Group,
    GroupCreate,
    GroupUpdate,
    GroupMember,
    GroupMemberCreate,
    GroupMemberUpdate,
)
from src.services import group as group_service

router = APIRouter()


# Проверка прав администратора
def check_admin_rights(current_user: User):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")


# Проверка прав тимлида в группе
async def check_team_lead_rights(db: AsyncSession, group_id: int, current_user: User):
    # Администратор имеет полные права
    if current_user.role == UserRole.ADMIN:
        return

    # Проверяем, является ли пользователь тимлидом в данной группе
    role = await group_service.get_user_role_in_group(db=db, group_id=group_id, user_id=current_user.id)
    if role != GroupRole.TEAM_LEAD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль TeamLead в данной группе",
        )


@router.post("/", response_model=Group, status_code=status.HTTP_201_CREATED)
async def create_group(
    *,
    db: AsyncSession = Depends(get_db),
    group_in: GroupCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Создать новую группу.
    Доступно только для администраторов и тимлидов.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEAM_LEAD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    # Проверяем, существует ли группа с таким именем
    group = await group_service.get_by_name(db=db, name=group_in.name)
    if group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Группа с таким именем уже существует",
        )

    # Создаем группу
    group = await group_service.create(db=db, obj_in=group_in)

    # Если группу создал тимлид, добавляем его в группу с ролью тимлида
    if current_user.role == UserRole.TEAM_LEAD:
        await group_service.add_user_to_group(
            db=db, group_id=group.id, user_id=current_user.id, role=GroupRole.TEAM_LEAD
        )

    return group


@router.get("/", response_model=List[Group])
async def read_groups(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Получить список всех групп.
    """
    groups = await group_service.get_multi(db=db, skip=skip, limit=limit)
    return groups


@router.get("/{group_id}", response_model=Group)
async def read_group(
    *,
    db: AsyncSession = Depends(get_db),
    group_id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Получить информацию о конкретной группе по ID.
    """
    group = await group_service.get(db=db, id=group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с ID {group_id} не найдена",
        )
    return group


@router.put("/{group_id}", response_model=Group)
async def update_group(
    *,
    db: AsyncSession = Depends(get_db),
    group_id: int,
    group_in: GroupUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Обновить информацию о группе.
    Доступно для администраторов и тимлидов группы.
    """
    group = await group_service.get(db=db, id=group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с ID {group_id} не найдена",
        )

    # Проверяем права
    await check_team_lead_rights(db=db, group_id=group_id, current_user=current_user)

    group = await group_service.update(db=db, db_obj=group, obj_in=group_in)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    *,
    db: AsyncSession = Depends(get_db),
    group_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Удалить группу.
    Доступно только для администраторов.
    """
    check_admin_rights(current_user)

    group = await group_service.get(db=db, id=group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с ID {group_id} не найдена",
        )

    await group_service.delete(db=db, id=group_id)
    return None


@router.post("/{group_id}/members", response_model=GroupMember)
async def add_member_to_group(
    *,
    db: AsyncSession = Depends(get_db),
    group_id: int,
    member_in: GroupMemberCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Добавить пользователя в группу.
    Доступно для администраторов и тимлидов группы.
    """
    # Проверяем существование группы
    group = await group_service.get(db=db, id=group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с ID {group_id} не найдена",
        )

    # Проверяем права
    await check_team_lead_rights(db=db, group_id=group_id, current_user=current_user)

    # Проверяем, состоит ли пользователь уже в группе
    if await group_service.is_user_in_group(db=db, group_id=group_id, user_id=member_in.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь уже состоит в этой группе",
        )

    # Добавляем пользователя в группу
    member = await group_service.add_user_to_group(
        db=db, group_id=group_id, user_id=member_in.user_id, role=member_in.role
    )

    return member


@router.get("/{group_id}/members", response_model=List[GroupMember])
async def read_group_members(
    *,
    db: AsyncSession = Depends(get_db),
    group_id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Получить список всех участников группы.
    """
    # Проверяем существование группы
    group = await group_service.get(db=db, id=group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с ID {group_id} не найдена",
        )

    members = await group_service.get_group_members(db=db, group_id=group_id)
    return members


@router.put("/{group_id}/members/{user_id}", response_model=GroupMember)
async def update_member_role(
    *,
    db: AsyncSession = Depends(get_db),
    group_id: int,
    user_id: int,
    role_in: GroupMemberUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Обновить роль пользователя в группе.
    Доступно для администраторов и тимлидов группы.
    """
    # Проверяем права
    await check_team_lead_rights(db=db, group_id=group_id, current_user=current_user)

    # Проверяем, состоит ли пользователь в группе
    if not await group_service.is_user_in_group(db=db, group_id=group_id, user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден в группе",
        )

    # Обновляем роль пользователя
    member = await group_service.update_user_role(db=db, group_id=group_id, user_id=user_id, role=role_in.role)

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не удалось обновить роль пользователя",
        )

    return member


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member_from_group(
    *,
    db: AsyncSession = Depends(get_db),
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Удалить пользователя из группы.
    Доступно для администраторов и тимлидов группы.
    """
    # Проверяем права
    await check_team_lead_rights(db=db, group_id=group_id, current_user=current_user)

    # Нельзя удалить самого себя из группы, если ты тимлид
    if user_id == current_user.id and current_user.role != UserRole.ADMIN:
        role = await group_service.get_user_role_in_group(db=db, group_id=group_id, user_id=current_user.id)
        if role == GroupRole.TEAM_LEAD:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Тимлид не может удалить себя из группы",
            )

    result = await group_service.remove_user_from_group(db=db, group_id=group_id, user_id=user_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден в группе",
        )

    return None
