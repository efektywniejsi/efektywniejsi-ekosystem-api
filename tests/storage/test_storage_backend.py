"""Unit tests for storage backend extensions."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.core.storage import LocalStorage, StorageObject


class TestLocalStorageListObjects:
    """Tests for LocalStorage.list_objects method."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary directory for storage testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LocalStorage(tmpdir), tmpdir

    def test_list_objects_empty_folder(self, temp_storage):
        """Returns empty list for non-existent folder."""
        storage, _ = temp_storage
        result = storage.list_objects("avatars")
        assert result == []

    def test_list_objects_with_files(self, temp_storage):
        """Lists files in folder correctly."""
        storage, tmpdir = temp_storage

        # Create folder and files
        avatars_dir = Path(tmpdir) / "avatars"
        avatars_dir.mkdir()
        (avatars_dir / "file1.jpg").write_bytes(b"test content 1")
        (avatars_dir / "file2.png").write_bytes(b"test content 22")

        result = storage.list_objects("avatars")

        assert len(result) == 2
        keys = {obj.key for obj in result}
        assert "avatars/file1.jpg" in keys
        assert "avatars/file2.png" in keys

    def test_list_objects_returns_storage_objects(self, temp_storage):
        """Returns proper StorageObject instances with metadata."""
        storage, tmpdir = temp_storage

        avatars_dir = Path(tmpdir) / "avatars"
        avatars_dir.mkdir()
        test_file = avatars_dir / "test.jpg"
        test_file.write_bytes(b"x" * 100)

        result = storage.list_objects("avatars")

        assert len(result) == 1
        obj = result[0]
        assert isinstance(obj, StorageObject)
        assert obj.key == "avatars/test.jpg"
        assert obj.size == 100
        assert isinstance(obj.last_modified, datetime)
        assert obj.last_modified.tzinfo == UTC

    def test_list_objects_recursive(self, temp_storage):
        """Lists files in nested folders."""
        storage, tmpdir = temp_storage

        # Create nested structure
        nested_dir = Path(tmpdir) / "attachments" / "2024" / "01"
        nested_dir.mkdir(parents=True)
        (nested_dir / "deep_file.pdf").write_bytes(b"nested content")
        (Path(tmpdir) / "attachments" / "root_file.pdf").write_bytes(b"root content")

        result = storage.list_objects("attachments")

        assert len(result) == 2
        keys = {obj.key for obj in result}
        assert "attachments/root_file.pdf" in keys
        assert "attachments/2024/01/deep_file.pdf" in keys


class TestLocalStoragePathTraversal:
    """Tests for path traversal protection."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary directory for storage testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LocalStorage(tmpdir), tmpdir

    def test_delete_rejects_path_traversal(self, temp_storage):
        """delete() should reject paths that escape base directory."""
        storage, _ = temp_storage

        with pytest.raises(ValueError, match="Path traversal"):
            storage.delete("../../../etc/passwd")

    def test_delete_rejects_absolute_path(self, temp_storage):
        """delete() should reject absolute paths."""
        storage, _ = temp_storage

        with pytest.raises(ValueError, match="Path traversal"):
            storage.delete("/etc/passwd")

    def test_exists_rejects_path_traversal(self, temp_storage):
        """exists() should reject paths that escape base directory."""
        storage, _ = temp_storage

        with pytest.raises(ValueError, match="Path traversal"):
            storage.exists("../../../etc/passwd")

    def test_delete_works_for_valid_path(self, temp_storage):
        """delete() should work for valid paths within base directory."""
        storage, tmpdir = temp_storage

        # Create a test file
        avatars_dir = Path(tmpdir) / "avatars"
        avatars_dir.mkdir()
        test_file = avatars_dir / "test.jpg"
        test_file.write_bytes(b"test content")

        # Should not raise
        storage.delete("avatars/test.jpg")
        assert not test_file.exists()

    def test_upload_returns_key_not_path(self, temp_storage):
        """upload() should return a storage key, not a filesystem path."""
        storage, tmpdir = temp_storage

        result = storage.upload(b"content", "avatars", "test.jpg")

        assert result == "avatars/test.jpg"
        assert not result.startswith(tmpdir)
