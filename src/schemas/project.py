from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Базовая схема для проекта
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    group_id: int

# Схема для создания проекта
class ProjectCreate(ProjectBase):
    pass

# Схема для обновления проекта
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    group_id: Optional[int] = None

# Схема для получения проекта из БД
class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Схема для получения проекта с задачами
class ProjectWithTasks(Project):
    tasks: List = []