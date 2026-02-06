"""Service for identifying and cleaning up orphaned storage files."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.community.models.thread_attachment import ThreadAttachment
from app.core.config import settings
from app.core.storage import StorageObject, get_storage
from app.courses.models.attachment import Attachment
from app.courses.models.course import Course

logger = logging.getLogger(__name__)


def _extract_key_from_avatar_url(url: str | None) -> str | None:
    """Extract storage key from avatar URL.

    Avatar URLs can be:
    - Full R2 URL: https://files.example.com/avatars/xxx.jpg -> avatars/xxx.jpg
    - Local URL: http://localhost:8000/uploads/avatars/xxx.jpg -> avatars/xxx.jpg
    """
    if not url:
        return None

    # Look for avatars/ in the URL path
    if "/avatars/" in url:
        idx = url.find("/avatars/")
        return url[idx + 1 :]  # Remove leading slash, keep "avatars/xxx.jpg"

    # Already a key
    if url.startswith("avatars/"):
        return url

    return None


def _extract_key_from_thumbnail_url(url: str | None) -> str | None:
    """Extract storage key from thumbnail URL.

    Thumbnail URLs are API routes like:
    /api/v1/courses/{id}/learning-thumbnail/{filename}

    The actual file is stored at: thumbnails/{filename}
    """
    if not url:
        return None

    # Extract filename from the API URL path
    if "/learning-thumbnail/" in url:
        filename = url.split("/")[-1]
        if filename:
            return f"thumbnails/{filename}"

    # Already a key
    if url.startswith("thumbnails/"):
        return url

    return None


def _get_avatar_keys(db: Session) -> set[str]:
    """Get all avatar keys from User.avatar_url."""
    rows = db.query(User.avatar_url).filter(User.avatar_url.isnot(None)).all()
    keys: set[str] = set()
    for (url,) in rows:
        if url:
            key = _extract_key_from_avatar_url(url)
            if key:
                keys.add(key)
    return keys


def _get_thumbnail_keys(db: Session) -> set[str]:
    """Get all thumbnail keys from Course.learning_thumbnail_url."""
    rows = (
        db.query(Course.learning_thumbnail_url)
        .filter(Course.learning_thumbnail_url.isnot(None))
        .all()
    )
    keys: set[str] = set()
    for (url,) in rows:
        if url:
            key = _extract_key_from_thumbnail_url(url)
            if key:
                keys.add(key)
    return keys


def _get_attachment_keys(db: Session) -> set[str]:
    """Get all attachment keys from Attachment.file_path."""
    rows = db.query(Attachment.file_path).all()
    return {path for (path,) in rows if path}


def _get_thread_attachment_keys(db: Session) -> set[str]:
    """Get all thread attachment keys from ThreadAttachment.file_path."""
    rows = db.query(ThreadAttachment.file_path).all()
    return {path for (path,) in rows if path}


# Folder configurations for cleanup
FOLDER_CONFIGS = [
    ("avatars", _get_avatar_keys),
    ("thumbnails", _get_thumbnail_keys),
    ("attachments", _get_attachment_keys),
    ("thread-attachments", _get_thread_attachment_keys),
]


class CleanupService:
    """Service for identifying and cleaning up orphaned storage files.

    This service scans storage folders, compares against database references,
    and identifies files that exist in storage but are not referenced anywhere.
    """

    @staticmethod
    def find_orphaned_files(
        db: Session,
        grace_hours: int | None = None,
    ) -> tuple[list[StorageObject], dict[str, set[str]]]:
        """Find all orphaned files across all storage folders.

        Args:
            db: Database session
            grace_hours: Don't mark files newer than this as orphaned.
                        Defaults to settings.STORAGE_CLEANUP_GRACE_HOURS.

        Returns:
            Tuple of (orphaned_files, referenced_keys_by_folder)
        """
        if grace_hours is None:
            grace_hours = settings.STORAGE_CLEANUP_GRACE_HOURS

        cutoff_time = datetime.now(UTC) - timedelta(hours=grace_hours)
        storage = get_storage()

        orphaned_files: list[StorageObject] = []
        referenced_by_folder: dict[str, set[str]] = {}

        for prefix, get_referenced_keys in FOLDER_CONFIGS:
            # Get all files in storage folder
            try:
                storage_files = storage.list_objects(prefix)
            except Exception as e:
                logger.error(f"Failed to list objects in {prefix}/: {e}")
                continue

            logger.info(f"Found {len(storage_files)} files in {prefix}/")

            # Get all referenced keys from DB
            try:
                referenced_keys = get_referenced_keys(db)
            except Exception as e:
                logger.error(f"Failed to get referenced keys for {prefix}/: {e}")
                continue

            referenced_by_folder[prefix] = referenced_keys
            logger.info(f"Found {len(referenced_keys)} referenced keys for {prefix}/")

            # Find orphans (in storage but not in DB)
            for obj in storage_files:
                if obj.key not in referenced_keys:
                    # Ensure last_modified is timezone-aware
                    obj_modified = obj.last_modified
                    if obj_modified.tzinfo is None:
                        obj_modified = obj_modified.replace(tzinfo=UTC)

                    # Check grace period
                    if obj_modified < cutoff_time:
                        orphaned_files.append(obj)
                        logger.debug(f"Orphaned: {obj.key} (modified: {obj_modified})")
                    else:
                        age_hours = (datetime.now(UTC) - obj_modified).total_seconds() / 3600
                        logger.debug(
                            f"Skipping {obj.key}: too recent ({age_hours:.1f}h old, "
                            f"grace period is {grace_hours}h)"
                        )

        logger.info(f"Total orphaned files found: {len(orphaned_files)}")
        return orphaned_files, referenced_by_folder

    @staticmethod
    def delete_orphaned_files(
        orphaned_files: list[StorageObject],
        dry_run: bool = False,
        batch_size: int | None = None,
    ) -> tuple[int, int, list[str]]:
        """Delete orphaned files in batches.

        Args:
            orphaned_files: List of files to delete
            dry_run: If True, only log what would be deleted
            batch_size: Number of files to process before logging progress.
                       Defaults to settings.STORAGE_CLEANUP_BATCH_SIZE.

        Returns:
            Tuple of (deleted_count, deleted_size_bytes, errors)
        """
        if batch_size is None:
            batch_size = settings.STORAGE_CLEANUP_BATCH_SIZE

        storage = get_storage()
        deleted_count = 0
        deleted_size = 0
        errors: list[str] = []

        for i, obj in enumerate(orphaned_files):
            try:
                if not dry_run:
                    storage.delete(obj.key)
                deleted_count += 1
                deleted_size += obj.size

                action = "[DRY-RUN] Would delete" if dry_run else "Deleted"
                logger.info(f"{action}: {obj.key} ({obj.size} bytes)")

                # Log progress periodically
                if (i + 1) % batch_size == 0:
                    logger.info(f"Processed {i + 1}/{len(orphaned_files)} files...")

            except Exception as e:
                error_msg = f"Failed to delete {obj.key}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        return deleted_count, deleted_size, errors
