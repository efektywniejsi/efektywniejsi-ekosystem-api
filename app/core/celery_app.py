import ssl

from celery import Celery
from celery.schedules import crontab

import app.db.base  # noqa: F401 — register all models so relationships resolve
from app.core.config import settings

_uses_tls = settings.REDIS_URL.startswith("rediss://")

celery_app = Celery(
    "efektywniejsi",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Warsaw",
    task_track_started=True,
    result_expires=3600,
    beat_schedule={
        "cleanup-orphaned-files-daily": {
            "task": "app.storage.tasks.cleanup_orphaned_files_task",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM Warsaw time
            "kwargs": {"dry_run": False},
        },
    },
)

if _uses_tls:
    celery_app.conf.update(
        broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
        redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
    )

celery_app.autodiscover_tasks(["app.ai", "app.notifications", "app.storage"])
