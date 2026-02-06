"""Celery tasks for storage cleanup operations."""

import logging
import time
from typing import Any

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.storage.services.cleanup_service import CleanupService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=0)
def cleanup_orphaned_files_task(
    self: Any,
    dry_run: bool | None = None,
    grace_hours: int | None = None,
) -> dict[str, Any]:
    """Clean up orphaned files from storage.

    This task:
    1. Lists all files in each storage folder (avatars, thumbnails, attachments, thread-attachments)
    2. Queries database for referenced file paths
    3. Identifies orphaned files (in storage but not in DB)
    4. Deletes orphaned files (respecting grace period)

    Args:
        dry_run: If True, only log what would be deleted.
                Defaults to settings.STORAGE_CLEANUP_DRY_RUN.
        grace_hours: Don't delete files newer than this.
                    Defaults to settings.STORAGE_CLEANUP_GRACE_HOURS.

    Returns:
        Dict with cleanup results including deleted_count, deleted_size_bytes,
        by_folder breakdown, errors list, and execution time.
    """
    start_time = time.time()

    if dry_run is None:
        dry_run = settings.STORAGE_CLEANUP_DRY_RUN
    if grace_hours is None:
        grace_hours = settings.STORAGE_CLEANUP_GRACE_HOURS

    logger.info(f"Starting orphaned file cleanup (dry_run={dry_run}, grace_hours={grace_hours})")

    db = SessionLocal()
    try:
        # Find orphaned files
        orphaned_files, _ = CleanupService.find_orphaned_files(db, grace_hours)

        if not orphaned_files:
            logger.info("No orphaned files found")
            return {
                "deleted_count": 0,
                "deleted_size_bytes": 0,
                "by_folder": {},
                "errors": [],
                "dry_run": dry_run,
                "execution_time_seconds": time.time() - start_time,
            }

        # Group by folder for reporting
        by_folder: dict[str, int] = {}
        for obj in orphaned_files:
            folder = obj.key.split("/")[0]
            by_folder[folder] = by_folder.get(folder, 0) + 1

        # Delete orphaned files
        deleted_count, deleted_size, errors = CleanupService.delete_orphaned_files(
            orphaned_files,
            dry_run=dry_run,
        )

        execution_time = time.time() - start_time

        logger.info(
            f"Cleanup complete: deleted={deleted_count}, size={deleted_size} bytes, "
            f"errors={len(errors)}, time={execution_time:.2f}s, dry_run={dry_run}"
        )

        return {
            "deleted_count": deleted_count,
            "deleted_size_bytes": deleted_size,
            "by_folder": by_folder,
            "errors": errors,
            "dry_run": dry_run,
            "execution_time_seconds": execution_time,
        }

    except Exception as exc:
        logger.exception(f"Orphaned file cleanup failed: {exc}")
        raise
    finally:
        db.close()
