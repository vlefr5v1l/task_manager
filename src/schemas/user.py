from typing import Optional

from pydantic import BaseModel, EmailStr

from src.models.user import UserRole


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: Optional[UserRole] = UserRole.DEVELOPER


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserInDBBase(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class User(UserInDBBase):
    id: int

    class Config:
        from_attributes = True


class UserInDB(UserInDBBase):
    password_hash: str
