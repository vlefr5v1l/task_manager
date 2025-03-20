from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate
from src.core.security import get_password_hash, verify_password


async def get(db: AsyncSession, id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == id))
    return result.scalars().first()


async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def create(db: AsyncSession, *, obj_in: UserCreate) -> User:
    db_obj = User(
        username=obj_in.username,
        email=obj_in.email,
        password_hash=get_password_hash(obj_in.password),
        full_name=obj_in.full_name,
        role=obj_in.role
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update(db: AsyncSession, *, db_obj: User, obj_in: UserUpdate) -> User:
    obj_data = obj_in.dict(exclude_unset=True)
    if obj_data.get("password"):
        obj_data["password_hash"] = get_password_hash(obj_data.pop("password"))

    for field, value in obj_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def authenticate(db: AsyncSession, *, email: str, password: str) -> Optional[User]:
    user = await get_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user