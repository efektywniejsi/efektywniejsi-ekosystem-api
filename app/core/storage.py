import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import settings


@dataclass
class StorageObject:
    """Represents a file object in storage."""

    key: str
    last_modified: datetime
    size: int


class StorageBackend(Protocol):
    def upload(self, file_content: bytes, folder: str, filename: str) -> str:
        """Upload file and return the stored path/key."""
        ...

    def download_url(self, path: str) -> str:
        """Return a URL to download the file."""
        ...

    def delete(self, path: str) -> None:
        """Delete a file by its path/key."""
        ...

    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        ...

    def list_objects(self, prefix: str) -> list[StorageObject]:
        """List all objects with the given prefix/folder."""
        ...


class LocalStorage:
    """Local filesystem storage for development."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)

    def upload(self, file_content: bytes, folder: str, filename: str) -> str:
        upload_dir = self._base_dir / folder
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        return f"{folder}/{filename}"

    def download_url(self, path: str) -> str:
        return f"{settings.BACKEND_URL}/uploads/{path}"

    def _resolve_safe_path(self, path: str) -> Path:
        """Resolve path and validate it stays within base directory."""
        base_resolved = self._base_dir.resolve()
        full_path = (self._base_dir / path).resolve()
        if (
            not str(full_path).startswith(str(base_resolved) + os.sep)
            and full_path != base_resolved
        ):
            raise ValueError(f"Path traversal attempt detected: {path}")
        return full_path

    def delete(self, path: str) -> None:
        full_path = self._resolve_safe_path(path)
        if full_path.exists():
            full_path.unlink()

    def exists(self, path: str) -> bool:
        full_path = self._resolve_safe_path(path)
        return full_path.exists()

    def list_objects(self, prefix: str) -> list[StorageObject]:
        """List all files in the given folder (recursively)."""
        folder_path = self._base_dir / prefix
        if not folder_path.exists():
            return []

        result = []
        for file_path in folder_path.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                relative_path = file_path.relative_to(self._base_dir)
                result.append(
                    StorageObject(
                        key=str(relative_path),
                        last_modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                        size=stat.st_size,
                    )
                )
        return result


class R2Storage:
    """Cloudflare R2 storage (S3-compatible) for production."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
            region_name="auto",
        )
        self._bucket = settings.R2_BUCKET_NAME

    def upload(self, file_content: bytes, folder: str, filename: str) -> str:
        key = f"{folder}/{filename}"
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=file_content,
        )
        return key

    def download_url(self, path: str) -> str:
        if settings.R2_PUBLIC_URL:
            return f"{settings.R2_PUBLIC_URL}/{path}"
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": path},
            ExpiresIn=3600,
        )
        return url

    def delete(self, path: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=path)

    def exists(self, path: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=path)
            return True
        except self._client.exceptions.ClientError:
            return False

    def list_objects(self, prefix: str) -> list[StorageObject]:
        """List all objects in R2 with the given prefix."""
        result = []
        paginator = self._client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                result.append(
                    StorageObject(
                        key=obj["Key"],
                        last_modified=obj["LastModified"],
                        size=obj["Size"],
                    )
                )
        return result


def get_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "r2":
        return R2Storage()
    return LocalStorage(settings.UPLOAD_DIR)


def generate_unique_filename(original_filename: str) -> str:
    extension = Path(original_filename).suffix
    return f"{uuid.uuid4()}{extension}"
