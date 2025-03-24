from celery import Celery
from src.core.config import settings
from celery.schedules import crontab


celery_app = Celery(
    "worker",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
)

celery_app.conf.task_routes = {"src.worker.tasks.*": {"queue": "main_queue"}}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["src.worker.tasks"])

celery_app.conf.beat_schedule = {
    "check-task-deadlines": {
        "task": "src.worker.tasks.check_task_deadlines",
        "schedule": crontab(hour="*", minute="0"),  # Каждый час
    },
    "generate-daily-reports": {
        "task": "src.worker.tasks.generate_reports",
        "schedule": crontab(hour="0", minute="0"),  # Каждый день в полночь
    },
}
