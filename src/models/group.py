from sqlalchemy import Column, String, Integer, ForeignKey, Enum
from src.db.base import Base
import enum


class GroupRole(str, enum.Enum):
    TEAM_LEAD = "team_lead"
    DEVELOPER = "developer"
    OBSERVER = "observer"


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)

    # Отношения перенесены в relationships.py


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    role = Column(Enum(GroupRole), default=GroupRole.DEVELOPER)

    # Отношения перенесены в relationships.py
