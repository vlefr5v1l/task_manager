# Импорт всех моделей в правильном порядке
from src.models.user import User, UserRole

# from src.models.group import Group, GroupMember, GroupRole
from src.models.project import Project
from src.models.task import Task, Comment, TaskStatus, TaskPriority

from src.models.relationships import *
