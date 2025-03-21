from pydantic import BaseModel, Field
from typing import Optional, List
from src.models.group import GroupRole


class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Group(GroupBase):
    id: int

    class Config:
        from_attributes = True


class GroupMemberBase(BaseModel):
    user_id: int
    role: GroupRole = GroupRole.DEVELOPER


class GroupMemberCreate(GroupMemberBase):
    pass


class GroupMemberUpdate(BaseModel):
    role: GroupRole


class GroupMember(GroupMemberBase):
    id: int
    group_id: int

    class Config:
        from_attributes = True


class GroupWithMembers(Group):
    members: List[GroupMember] = []
