"""Unit tests for admin cleanup API endpoints.

These tests use mocks instead of testcontainers for fast, isolated testing.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.storage import StorageObject
from app.db.session import get_db
from app.storage.routes.admin_cleanup import router


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    user = MagicMock(spec=User)
    user.id = "admin-uuid"
    user.email = "admin@test.com"
    user.role = "admin"
    return user


@pytest.fixture
def mock_regular_user():
    """Mock regular user."""
    user = MagicMock(spec=User)
    user.id = "user-uuid"
    user.email = "user@test.com"
    user.role = "paid"
    return user


@pytest.fixture
def app_with_admin(mock_db, mock_admin_user):
    """Create FastAPI app with admin user authenticated."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/admin")

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin_user

    return app


@pytest.fixture
def app_with_regular_user(mock_db, mock_regular_user):
    """Create FastAPI app with regular user (should be rejected)."""
    from fastapi import HTTPException, status

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/admin")

    app.dependency_overrides[get_db] = lambda: mock_db

    def reject_non_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    app.dependency_overrides[require_admin] = reject_non_admin

    return app


@pytest.fixture
def admin_client(app_with_admin):
    """Test client with admin authentication."""
    return TestClient(app_with_admin)


@pytest.fixture
def user_client(app_with_regular_user):
    """Test client with regular user authentication."""
    return TestClient(app_with_regular_user)


@pytest.fixture
def mock_storage():
    """Mock storage backend that returns empty by default."""
    storage = MagicMock()
    storage.list_objects.return_value = []
    return storage


def create_folder_specific_storage(folder: str, objects: list):
    """Create mock storage that returns objects only for specific folder."""
    storage = MagicMock()

    def list_objects_by_folder(prefix):
        if prefix == folder:
            return objects
        return []

    storage.list_objects.side_effect = list_objects_by_folder
    return storage


class TestPreviewOrphanedFiles:
    """Tests for GET /api/v1/admin/storage/orphaned-files/preview."""

    def test_requires_admin(self, user_client):
        """Regular users cannot access preview endpoint."""
        response = user_client.get("/api/v1/admin/storage/orphaned-files/preview")
        assert response.status_code == 403

    def test_admin_can_access(self, admin_client, mock_storage):
        """Admin users can access preview endpoint."""
        with patch(
            "app.storage.services.cleanup_service.get_storage",
            return_value=mock_storage,
        ):
            response = admin_client.get("/api/v1/admin/storage/orphaned-files/preview")

        assert response.status_code == 200
        data = response.json()
        assert "total_orphaned" in data
        assert "total_size_bytes" in data
        assert "files" in data
        assert data["dry_run"] is True

    def test_returns_orphaned_files(self, admin_client):
        """Preview returns list of orphaned files."""
        old_time = datetime.now(UTC) - timedelta(days=2)
        folder_storage = create_folder_specific_storage(
            "avatars",
            [StorageObject(key="avatars/orphan.jpg", last_modified=old_time, size=1000)],
        )

        with patch(
            "app.storage.services.cleanup_service.get_storage",
            return_value=folder_storage,
        ):
            response = admin_client.get("/api/v1/admin/storage/orphaned-files/preview")

        assert response.status_code == 200
        data = response.json()
        assert data["total_orphaned"] == 1
        assert data["total_size_bytes"] == 1000
        assert len(data["files"]) == 1
        assert data["files"][0]["key"] == "avatars/orphan.jpg"

    def test_grace_hours_validation(self, admin_client):
        """grace_hours must be at least 1."""
        response = admin_client.get("/api/v1/admin/storage/orphaned-files/preview?grace_hours=0")
        assert response.status_code == 422  # Validation error

    def test_custom_grace_hours(self, admin_client, mock_storage):
        """Custom grace_hours parameter is respected."""
        old_time = datetime.now(UTC) - timedelta(hours=5)
        mock_storage.list_objects.return_value = [
            StorageObject(key="avatars/file.jpg", last_modified=old_time, size=100),
        ]

        with patch(
            "app.storage.services.cleanup_service.get_storage",
            return_value=mock_storage,
        ):
            # With 10h grace, file should NOT be orphaned
            response = admin_client.get(
                "/api/v1/admin/storage/orphaned-files/preview?grace_hours=10"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_orphaned"] == 0  # File is within grace period


class TestTriggerCleanup:
    """Tests for POST /api/v1/admin/storage/orphaned-files/cleanup."""

    def test_requires_admin(self, user_client):
        """Regular users cannot trigger cleanup."""
        response = user_client.post("/api/v1/admin/storage/orphaned-files/cleanup")
        assert response.status_code == 403

    def test_dry_run_default_true(self, admin_client, mock_storage):
        """Default is dry_run=true for safety."""
        with patch(
            "app.storage.services.cleanup_service.get_storage",
            return_value=mock_storage,
        ):
            response = admin_client.post("/api/v1/admin/storage/orphaned-files/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True
        mock_storage.delete.assert_not_called()

    def test_actual_cleanup_requires_explicit_flag(self, admin_client):
        """Actual deletion requires dry_run=false."""
        old_time = datetime.now(UTC) - timedelta(days=2)
        folder_storage = create_folder_specific_storage(
            "avatars",
            [StorageObject(key="avatars/orphan.jpg", last_modified=old_time, size=1000)],
        )

        with patch(
            "app.storage.services.cleanup_service.get_storage",
            return_value=folder_storage,
        ):
            response = admin_client.post(
                "/api/v1/admin/storage/orphaned-files/cleanup?dry_run=false"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is False
        assert data["deleted_count"] == 1
        folder_storage.delete.assert_called_once()

    def test_async_mode_returns_task_id(self, admin_client):
        """async_mode=true returns task ID."""
        with patch("app.storage.routes.admin_cleanup.cleanup_orphaned_files_task") as mock_task:
            mock_task.delay.return_value.id = "test-task-id-123"

            response = admin_client.post(
                "/api/v1/admin/storage/orphaned-files/cleanup?async_mode=true"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id-123"
        assert data["status"] == "queued"

    def test_grace_hours_validation(self, admin_client):
        """grace_hours must be at least 1."""
        response = admin_client.post("/api/v1/admin/storage/orphaned-files/cleanup?grace_hours=0")
        assert response.status_code == 422  # Validation error

    def test_returns_cleanup_stats(self, admin_client):
        """Response includes cleanup statistics."""
        old_time = datetime.now(UTC) - timedelta(days=2)
        folder_storage = create_folder_specific_storage(
            "avatars",
            [
                StorageObject(key="avatars/file1.jpg", last_modified=old_time, size=100),
                StorageObject(key="avatars/file2.jpg", last_modified=old_time, size=200),
            ],
        )

        with patch(
            "app.storage.services.cleanup_service.get_storage",
            return_value=folder_storage,
        ):
            response = admin_client.post("/api/v1/admin/storage/orphaned-files/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 2
        assert data["deleted_size_bytes"] == 300
        assert data["by_folder"]["avatars"] == 2
        assert "execution_time_seconds" in data

    def test_reports_errors(self, admin_client):
        """Deletion errors are reported in response."""
        old_time = datetime.now(UTC) - timedelta(days=2)
        folder_storage = create_folder_specific_storage(
            "avatars",
            [StorageObject(key="avatars/file.jpg", last_modified=old_time, size=100)],
        )
        folder_storage.delete.side_effect = Exception("Storage error")

        with patch(
            "app.storage.services.cleanup_service.get_storage",
            return_value=folder_storage,
        ):
            response = admin_client.post(
                "/api/v1/admin/storage/orphaned-files/cleanup?dry_run=false"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
        assert len(data["errors"]) == 1
        assert "Storage error" in data["errors"][0]
