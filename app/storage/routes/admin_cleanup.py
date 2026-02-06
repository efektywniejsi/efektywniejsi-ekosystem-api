"""Admin routes for storage cleanup operations."""

import time

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.storage.schemas import (
    CleanupPreviewResponse,
    CleanupResultResponse,
    CleanupTaskResponse,
    OrphanedFile,
)
from app.storage.services.cleanup_service import CleanupService
from app.storage.tasks import cleanup_orphaned_files_task

router = APIRouter(prefix="/storage", tags=["admin-storage"])


@router.get("/orphaned-files/preview", response_model=CleanupPreviewResponse)
@limiter.limit("10/minute")
async def preview_orphaned_files(
    request: Request,
    grace_hours: int = Query(
        default=None,
        ge=1,
        description="Files newer than this (in hours) won't be marked as orphaned. "
        "Minimum 1 hour. Defaults to STORAGE_CLEANUP_GRACE_HOURS setting.",
    ),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> CleanupPreviewResponse:
    """Preview orphaned files that would be deleted.

    Use this endpoint to inspect orphaned files before triggering actual cleanup.
    This is a read-only operation that doesn't delete anything.
    """
    if grace_hours is None:
        grace_hours = settings.STORAGE_CLEANUP_GRACE_HOURS

    orphaned_files, _ = CleanupService.find_orphaned_files(db, grace_hours)

    by_folder: dict[str, int] = {}
    total_size = 0
    files: list[OrphanedFile] = []

    for obj in orphaned_files:
        folder = obj.key.split("/")[0]
        by_folder[folder] = by_folder.get(folder, 0) + 1
        total_size += obj.size
        files.append(
            OrphanedFile(
                key=obj.key,
                last_modified=obj.last_modified,
                size=obj.size,
                folder=folder,
            )
        )

    return CleanupPreviewResponse(
        total_orphaned=len(orphaned_files),
        total_size_bytes=total_size,
        by_folder=by_folder,
        files=files,
        grace_hours=grace_hours,
        dry_run=True,
    )


@router.post(
    "/orphaned-files/cleanup",
    response_model=CleanupResultResponse | CleanupTaskResponse,
)
@limiter.limit("2/minute")
async def trigger_cleanup(
    request: Request,
    dry_run: bool = Query(
        default=True,
        description="If true (default), only report what would be deleted without actual deletion. "
        "Set to false to actually delete files. Default is True for safety.",
    ),
    grace_hours: int = Query(
        default=None,
        ge=1,
        description="Files newer than this (in hours) won't be deleted. "
        "Minimum 1 hour. Defaults to STORAGE_CLEANUP_GRACE_HOURS setting.",
    ),
    async_mode: bool = Query(
        default=False,
        description="If true, run cleanup as a background Celery task. "
        "Returns task_id immediately.",
    ),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> CleanupResultResponse | CleanupTaskResponse:
    """Trigger orphaned file cleanup.

    By default runs synchronously with dry_run=True for safety.
    Set dry_run=False to actually delete files.
    Set async_mode=True to run as a background Celery task (recommended for large cleanups).
    """
    if grace_hours is None:
        grace_hours = settings.STORAGE_CLEANUP_GRACE_HOURS

    if async_mode:
        task = cleanup_orphaned_files_task.delay(
            dry_run=dry_run,
            grace_hours=grace_hours,
        )
        return CleanupTaskResponse(task_id=task.id, status="queued")

    # Synchronous execution
    start_time = time.time()

    orphaned_files, _ = CleanupService.find_orphaned_files(db, grace_hours)

    by_folder: dict[str, int] = {}
    for obj in orphaned_files:
        folder = obj.key.split("/")[0]
        by_folder[folder] = by_folder.get(folder, 0) + 1

    deleted_count, deleted_size, errors = CleanupService.delete_orphaned_files(
        orphaned_files,
        dry_run=dry_run,
    )

    return CleanupResultResponse(
        deleted_count=deleted_count,
        deleted_size_bytes=deleted_size,
        by_folder=by_folder,
        errors=errors,
        dry_run=dry_run,
        execution_time_seconds=time.time() - start_time,
    )
