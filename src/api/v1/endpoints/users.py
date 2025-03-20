from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.user import User, UserCreate
from src.services import user as user_service

router = APIRouter()


@router.get("/", response_model=List[User])
async def read_users(
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> Any:
    """Получить список всех пользователей"""
    users = await user_service.get_multi(db=db, skip=skip, limit=limit)
    return users
