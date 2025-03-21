from sqlalchemy.orm import relationship

from src.models.user import User
from src.models.group import Group, GroupMember
from src.models.project import Project
from src.models.task import Task, Comment

# Отношения для User
User.tasks_created = relationship("Task", back_populates="creator", foreign_keys="Task.created_by_id")
User.tasks_assigned = relationship("Task", back_populates="assignee", foreign_keys="Task.assigned_to_id")
User.group_memberships = relationship("GroupMember", back_populates="user")
User.comments = relationship("Comment", back_populates="user")

# Отношения для GroupMember
GroupMember.group = relationship("Group", back_populates="members")
GroupMember.user = relationship("User", back_populates="group_memberships")

# Отношения для Group
Group.members = relationship("GroupMember", back_populates="group")
Group.projects = relationship("Project", back_populates="group")

# Отношения для Project
Project.group = relationship("Group", back_populates="projects")
Project.tasks = relationship("Task", back_populates="project")

# Отношения для Task
Task.creator = relationship("User", back_populates="tasks_created", foreign_keys=[Task.created_by_id])
Task.assignee = relationship("User", back_populates="tasks_assigned", foreign_keys=[Task.assigned_to_id])
Task.project = relationship("Project", back_populates="tasks")
Task.comments = relationship("Comment", back_populates="task")

# Отношения для Comment
Comment.task = relationship("Task", back_populates="comments")
Comment.user = relationship("User", back_populates="comments")
