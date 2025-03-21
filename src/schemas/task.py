from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from src.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.NEW
    priority: TaskPriority = TaskPriority.MEDIUM
    project_id: int
    assigned_to_id: Optional[int] = None
    deadline: Optional[datetime] = Field(
        None, description="Срок выполнения задачи (UTC)"
    )


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    deadline: Optional[datetime] = None


class Task(TaskBase):
    id: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    pass


class Comment(CommentBase):
    id: int
    task_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaskWithComments(Task):
    comments: List[Comment] = []
