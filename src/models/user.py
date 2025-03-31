import enum

from sqlalchemy import Column, String, Integer, Enum, Boolean

from src.db.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEAM_LEAD = "team_lead"
    DEVELOPER = "developer"
    OBSERVER = "observer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Enum(UserRole), default=UserRole.DEVELOPER)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
