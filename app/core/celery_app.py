from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "efektywniejsi",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    result_expires=3600,
)

celery_app.autodiscover_tasks(["app.ai"])
