"""Pydantic schemas for storage cleanup operations."""

from datetime import datetime

from pydantic import BaseModel


class OrphanedFile(BaseModel):
    """Represents an orphaned file found in storage."""

    key: str
    last_modified: datetime
    size: int
    folder: str


class CleanupPreviewResponse(BaseModel):
    """Response for orphaned files preview endpoint."""

    total_orphaned: int
    total_size_bytes: int
    by_folder: dict[str, int]
    files: list[OrphanedFile]
    grace_hours: int
    dry_run: bool = True


class CleanupResultResponse(BaseModel):
    """Response for cleanup execution endpoint."""

    deleted_count: int
    deleted_size_bytes: int
    by_folder: dict[str, int]
    errors: list[str]
    dry_run: bool
    execution_time_seconds: float


class CleanupTaskResponse(BaseModel):
    """Response when cleanup is queued as async task."""

    task_id: str
    status: str = "queued"
