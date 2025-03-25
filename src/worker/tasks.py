import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.worker.celery_app import celery_app
from src.core.config import settings
from src.db.session import engine
from src.models.task import Task, TaskStatus
from src.models.user import User
from src.utils.service_notification import send_notification

logger = logging.getLogger(__name__)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task
def check_task_deadlines():
    """
    Проверяет задачи, у которых скоро истекает срок, и отправляет уведомления
    """
    logger.info("Checking task deadlines...")

    # Асинхронный код внутри синхронной задачи Celery
    async def _check_deadlines():
        async with AsyncSessionLocal() as session:
            # Ищем задачи с дедлайном в ближайшие 24 часа, которые не завершены
            tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
            today = datetime.now(timezone.utc)

            query = select(Task).where(
                and_(
                    Task.deadline >= today,
                    Task.deadline <= tomorrow,
                    Task.status.in_([TaskStatus.NEW, TaskStatus.IN_PROGRESS, TaskStatus.WAITING]),
                )
            )

            result = await session.execute(query)
            tasks = result.scalars().all()

            for task in tasks:
                # Получаем информацию о пользователе, которому назначена задача
                if task.assigned_to_id:
                    user_query = select(User).where(User.id == task.assigned_to_id)
                    user_result = await session.execute(user_query)
                    user = user_result.scalars().first()

                    if user:
                        # Отправляем уведомление
                        send_notification(
                            user_email=user.email,
                            subject=f"Срок задачи '{task.title}' скоро истекает",
                            message=f"Срок выполнения задачи '{task.title}' истекает через "
                            + f"{int((task.deadline - datetime.now(timezone.utc)).total_seconds() / 3600)} часов.",
                        )

    # Импортируем asyncio только в самой функции
    import asyncio

    asyncio.run(_check_deadlines())

    return {"status": "Deadline check completed"}


@celery_app.task
def generate_reports():
    """
    Генерирует отчеты по выполненным задачам
    """
    logger.info("Generating reports...")

    async def _generate_reports():
        async with AsyncSessionLocal() as session:
            # Запрос для подсчета задач по статусам
            query = select(Task.status, select(Task.id).filter(Task.status == Task.status).count())
            result = await session.execute(query)
            stats = result.all()

            # Формируем отчет
            report = "Отчет по статусам задач:\n"
            for status, count in stats:
                report += f"- {status.value}: {count} задач\n"

            logger.info(f"Report generated: {report}")

            # Можно сохранить отчет в файл или отправить по email
            # В этом примере просто логируем результат

    import asyncio

    asyncio.run(_generate_reports())

    return {"status": "Report generation completed"}
