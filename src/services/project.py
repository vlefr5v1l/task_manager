from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.project import Project
from src.repo import project as project_repo
from src.schemas.project import ProjectCreate, ProjectUpdate
from src.cache.client import get_cache, set_cache, delete_cache, invalidate_pattern
from src.schemas.project import ProjectCache
import logging

logger = logging.getLogger(__name__)


async def get(db: AsyncSession, id: int) -> Optional[Project]:
    # Сначала проверяем кэш
    cache_key = f"project:{id}"
    cached_project = await get_cache(cache_key)
    if cached_project:
        # Используем Pydantic для валидации и конвертации типов
        try:
            project_cache = ProjectCache(**cached_project)
            return project_cache.to_orm_model()
        except Exception as e:
            # Логируем ошибку и продолжаем получение из БД
            logger.warning(f"Error deserializing cached project {id}: {e}")
            # Инвалидируем неправильный кэш
            await delete_cache(cache_key)

    # Если в кэше нет или произошла ошибка, запрашиваем из БД
    project = await project_repo.get_project_by_id(db, id)

    # Кэшируем результат на 30 минут
    if project:
        await set_cache(
            cache_key,
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "group_id": project.group_id,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            },
            expires=1800,
        )

    return project


async def get_multi(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Project]:
    # Для списков тоже используем кэширование
    cache_key = f"projects:list:{skip}:{limit}"
    cached_projects = await get_cache(cache_key)
    if cached_projects:
        return [Project(**p) for p in cached_projects]

    projects = await project_repo.get_all_projects(db, skip=skip, limit=limit)

    # Кэшируем список на 5 минут
    if projects:
        await set_cache(
            cache_key,
            [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "group_id": p.group_id,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                }
                for p in projects
            ],
            expires=300,
        )

    return projects


async def get_by_group(db: AsyncSession, group_id: int, skip: int = 0, limit: int = 100) -> List[Project]:
    # Для списков по группам тоже используем кэширование
    cache_key = f"projects:group:{group_id}:{skip}:{limit}"
    cached_projects = await get_cache(cache_key)
    if cached_projects:
        return [Project(**p) for p in cached_projects]

    projects = await project_repo.get_projects_by_group(db, group_id, skip, limit)

    # Кэшируем список на 5 минут
    if projects:
        await set_cache(
            cache_key,
            [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "group_id": p.group_id,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                }
                for p in projects
            ],
            expires=300,
        )

    return projects


async def create(db: AsyncSession, *, obj_in: ProjectCreate) -> Project:
    # Создаем объект модели
    db_obj = Project(
        name=obj_in.name,
        description=obj_in.description,
        group_id=obj_in.group_id
    )

    # Сохраняем в базу данных через репозиторий
    await project_repo.create_project_in_db(db, db_obj)

    # Инвалидируем кэш списков проектов
    await invalidate_pattern("projects:list:*")
    if db_obj.group_id:
        await invalidate_pattern(f"projects:group:{db_obj.group_id}:*")

    return db_obj


async def update(db: AsyncSession, *, db_obj: Project, obj_in: ProjectUpdate) -> Project:
    # Сохраняем старый group_id, чтобы инвалидировать кэш правильно
    old_group_id = db_obj.group_id

    # Обновляем атрибуты объекта
    obj_data = obj_in.model_dump(exclude_unset=True)
    for field, value in obj_data.items():
        setattr(db_obj, field, value)

    # Обновляем в базе данных через репозиторий
    await project_repo.update_project_in_db(db, db_obj)

    # Инвалидируем кэш
    await delete_cache(f"project:{db_obj.id}")
    await invalidate_pattern("projects:list:*")

    # Если группа изменилась, инвалидируем кэш для обеих групп
    if old_group_id:
        await invalidate_pattern(f"projects:group:{old_group_id}:*")
    if db_obj.group_id and db_obj.group_id != old_group_id:
        await invalidate_pattern(f"projects:group:{db_obj.group_id}:*")

    return db_obj


async def delete(db: AsyncSession, *, id: int) -> bool:
    # Получаем проект для определения group_id перед удалением
    project = await project_repo.get_project_by_id(db, id)
    if not project:
        return False

    group_id = project.group_id

    # Удаляем через репозиторий
    result = await project_repo.delete_project_from_db(db, id)

    if result:
        # Инвалидируем кэш
        await delete_cache(f"project:{id}")
        await invalidate_pattern("projects:list:*")
        if group_id:
            await invalidate_pattern(f"projects:group:{group_id}:*")

    return result