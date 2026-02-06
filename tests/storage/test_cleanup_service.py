"""Unit tests for CleanupService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.storage import StorageObject
from app.storage.services.cleanup_service import (
    CleanupService,
    _extract_key_from_avatar_url,
    _extract_key_from_thumbnail_url,
)


class TestExtractKeyFromAvatarUrl:
    """Tests for _extract_key_from_avatar_url function."""

    def test_extract_from_r2_public_url(self):
        url = "https://files.efektywniejsi.pl/avatars/abc123.jpg"
        result = _extract_key_from_avatar_url(url)
        assert result == "avatars/abc123.jpg"

    def test_extract_from_local_url(self):
        url = "http://localhost:8000/uploads/avatars/abc123.jpg"
        result = _extract_key_from_avatar_url(url)
        assert result == "avatars/abc123.jpg"

    def test_extract_from_direct_key(self):
        key = "avatars/abc123.jpg"
        result = _extract_key_from_avatar_url(key)
        assert result == "avatars/abc123.jpg"

    def test_returns_none_for_invalid_url(self):
        url = "https://example.com/images/photo.jpg"
        result = _extract_key_from_avatar_url(url)
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = _extract_key_from_avatar_url("")
        assert result is None

    def test_returns_none_for_none(self):
        result = _extract_key_from_avatar_url(None)
        assert result is None


class TestExtractKeyFromThumbnailUrl:
    """Tests for _extract_key_from_thumbnail_url function."""

    def test_extract_from_api_url(self):
        url = "/api/v1/courses/123/learning-thumbnail/thumb-abc.jpg"
        result = _extract_key_from_thumbnail_url(url)
        assert result == "thumbnails/thumb-abc.jpg"

    def test_extract_from_full_api_url(self):
        url = "http://localhost:8000/api/v1/courses/456/learning-thumbnail/image.png"
        result = _extract_key_from_thumbnail_url(url)
        assert result == "thumbnails/image.png"

    def test_extract_from_direct_key(self):
        key = "thumbnails/abc123.jpg"
        result = _extract_key_from_thumbnail_url(key)
        assert result == "thumbnails/abc123.jpg"

    def test_returns_none_for_invalid_url(self):
        url = "https://example.com/images/photo.jpg"
        result = _extract_key_from_thumbnail_url(url)
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = _extract_key_from_thumbnail_url("")
        assert result is None


class TestFindOrphanedFiles:
    """Tests for find_orphaned_files method."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage that returns different results per folder."""
        storage = MagicMock()
        # Default: return empty list for all folders
        storage.list_objects.return_value = []
        return storage

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        # Default: return empty results for all queries
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.all.return_value = []
        return session

    def test_identifies_orphaned_avatar(self, mock_storage, mock_db_session):
        """Files in storage but not referenced in DB are marked orphaned."""
        # Mock: user has avatar at referenced.jpg
        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            ("https://files.example.com/avatars/referenced.jpg",)
        ]

        # Storage returns files only for avatars folder
        old_time = datetime.now(UTC) - timedelta(days=2)

        def list_objects_by_folder(prefix):
            if prefix == "avatars":
                return [
                    StorageObject(key="avatars/referenced.jpg", last_modified=old_time, size=100),
                    StorageObject(key="avatars/orphaned.jpg", last_modified=old_time, size=200),
                ]
            return []

        mock_storage.list_objects.side_effect = list_objects_by_folder

        with patch("app.storage.services.cleanup_service.get_storage", return_value=mock_storage):
            orphaned, _ = CleanupService.find_orphaned_files(mock_db_session, grace_hours=24)

        orphan_keys = {o.key for o in orphaned}
        assert "avatars/orphaned.jpg" in orphan_keys
        assert "avatars/referenced.jpg" not in orphan_keys

    def test_respects_grace_period(self, mock_storage, mock_db_session):
        """Files newer than grace period are not marked orphaned."""
        recent_time = datetime.now(UTC) - timedelta(hours=1)
        old_time = datetime.now(UTC) - timedelta(days=2)

        def list_objects_by_folder(prefix):
            if prefix == "avatars":
                return [
                    StorageObject(key="avatars/recent.jpg", last_modified=recent_time, size=100),
                    StorageObject(key="avatars/old.jpg", last_modified=old_time, size=200),
                ]
            return []

        mock_storage.list_objects.side_effect = list_objects_by_folder

        with patch("app.storage.services.cleanup_service.get_storage", return_value=mock_storage):
            orphaned, _ = CleanupService.find_orphaned_files(mock_db_session, grace_hours=24)

        orphan_keys = {o.key for o in orphaned}
        assert "avatars/old.jpg" in orphan_keys
        assert "avatars/recent.jpg" not in orphan_keys

    def test_identifies_orphaned_attachment(self, mock_storage, mock_db_session):
        """Attachment files not in DB are marked orphaned."""
        old_time = datetime.now(UTC) - timedelta(days=2)

        # Mock storage returns files only for attachments folder
        def list_objects_by_folder(prefix):
            if prefix == "attachments":
                return [
                    StorageObject(
                        key="attachments/referenced.pdf", last_modified=old_time, size=1000
                    ),
                    StorageObject(key="attachments/orphaned.pdf", last_modified=old_time, size=500),
                ]
            return []

        mock_storage.list_objects.side_effect = list_objects_by_folder

        # Mock DB: one attachment exists
        def mock_query(model):
            query_mock = MagicMock()
            # Check model name to return appropriate data
            model_name = (
                getattr(model, "__name__", "") if hasattr(model, "__name__") else str(model)
            )
            if "Attachment" in model_name and "Thread" not in model_name:
                query_mock.all.return_value = [("attachments/referenced.pdf",)]
            else:
                query_mock.all.return_value = []
                query_mock.filter.return_value.all.return_value = []
            return query_mock

        mock_db_session.query.side_effect = mock_query

        with patch("app.storage.services.cleanup_service.get_storage", return_value=mock_storage):
            orphaned, _ = CleanupService.find_orphaned_files(mock_db_session, grace_hours=24)

        orphan_keys = {o.key for o in orphaned}
        assert "attachments/orphaned.pdf" in orphan_keys
        assert "attachments/referenced.pdf" not in orphan_keys

    def test_handles_storage_error_gracefully(self, mock_storage, mock_db_session):
        """Storage errors for one folder don't stop processing of others."""
        mock_storage.list_objects.side_effect = Exception("Storage unavailable")

        with patch("app.storage.services.cleanup_service.get_storage", return_value=mock_storage):
            # Should not raise, just log error and continue
            orphaned, _ = CleanupService.find_orphaned_files(mock_db_session, grace_hours=24)

        assert orphaned == []

    def test_handles_naive_datetime(self, mock_storage, mock_db_session):
        """Handles files with naive datetime (no timezone)."""
        naive_time = datetime.now() - timedelta(days=2)  # No timezone

        def list_objects_by_folder(prefix):
            if prefix == "avatars":
                return [
                    StorageObject(key="avatars/file.jpg", last_modified=naive_time, size=100),
                ]
            return []

        mock_storage.list_objects.side_effect = list_objects_by_folder

        with patch("app.storage.services.cleanup_service.get_storage", return_value=mock_storage):
            orphaned, _ = CleanupService.find_orphaned_files(mock_db_session, grace_hours=24)

        # Should handle naive datetime without error
        assert len(orphaned) == 1


class TestDeleteOrphanedFiles:
    """Tests for delete_orphaned_files method."""

    def test_dry_run_does_not_delete(self):
        """Dry run should not call storage.delete()."""
        mock_storage = MagicMock()
        orphaned = [
            StorageObject(
                key="avatars/test.jpg",
                last_modified=datetime.now(UTC),
                size=100,
            ),
        ]

        with patch("app.storage.services.cleanup_service.get_storage", return_value=mock_storage):
            deleted, size, errors = CleanupService.delete_orphaned_files(orphaned, dry_run=True)

        assert deleted == 1
        assert size == 100
        assert len(errors) == 0
        mock_storage.delete.assert_not_called()

    def test_actual_deletion_calls_storage(self):
        """Actual deletion should call storage.delete()."""
        mock_storage = MagicMock()
        orphaned = [
            StorageObject(
                key="avatars/test.jpg",
                last_modified=datetime.now(UTC),
                size=100,
            ),
        ]

        with patch("app.storage.services.cleanup_service.get_storage", return_value=mock_storage):
            deleted, size, errors = CleanupService.delete_orphaned_files(orphaned, dry_run=False)

        assert deleted == 1
        assert size == 100
        mock_storage.delete.assert_called_once_with("avatars/test.jpg")

    def test_handles_deletion_errors(self):
        """Errors during deletion should be captured, not raised."""
        mock_storage = MagicMock()
        mock_storage.delete.side_effect = Exception("Storage error")
        orphaned = [
            StorageObject(
                key="avatars/test.jpg",
                last_modified=datetime.now(UTC),
                size=100,
            ),
        ]

        with patch("app.storage.services.cleanup_service.get_storage", return_value=mock_storage):
            deleted, size, errors = CleanupService.delete_orphaned_files(orphaned, dry_run=False)

        assert deleted == 0
        assert size == 0
        assert len(errors) == 1
        assert "Storage error" in errors[0]

    def test_batch_processing_multiple_files(self):
        """Processes multiple files correctly."""
        mock_storage = MagicMock()
        orphaned = [
            StorageObject(
                key=f"avatars/file{i}.jpg",
                last_modified=datetime.now(UTC),
                size=100 * (i + 1),
            )
            for i in range(5)
        ]

        with patch("app.storage.services.cleanup_service.get_storage", return_value=mock_storage):
            deleted, size, errors = CleanupService.delete_orphaned_files(orphaned, dry_run=False)

        assert deleted == 5
        assert size == 100 + 200 + 300 + 400 + 500  # 1500
        assert len(errors) == 0
        assert mock_storage.delete.call_count == 5
