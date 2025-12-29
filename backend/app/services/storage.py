"""
File storage abstractions.

Provides protocol and implementations for file storage backends:
- LocalFileStorage: Development/testing with local filesystem
- (Future: S3Storage, GCSStorage, etc.)

This module is intentionally generic and reusable across features
that need file storage (avatars, media uploads, exports, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from fastapi import UploadFile


class FileStorage(Protocol):
    """
    Protocol for file storage backends.

    Implementations must provide async upload and delete operations.
    The protocol enables dependency injection and easy testing.
    """

    async def upload(self, file: UploadFile, path: str) -> str:
        """
        Upload file to storage.

        Args:
            file: FastAPI UploadFile to store
            path: Relative path within storage (e.g., "avatars/123/uuid.jpg")

        Returns:
            Public URL or path to access the uploaded file
        """
        ...

    async def delete(self, path: str) -> bool:
        """
        Delete file from storage.

        Args:
            path: Relative path of file to delete

        Returns:
            True if file was deleted, False if not found
        """
        ...


class LocalFileStorage:
    """
    Local filesystem storage implementation.

    Suitable for development and testing. Stores files in a local
    directory and returns URLs relative to a base URL.

    For production, consider using cloud storage (S3, GCS, etc.)
    with appropriate implementations of the FileStorage protocol.
    """

    def __init__(self, base_path: Path, base_url: str) -> None:
        """
        Initialize local file storage.

        Args:
            base_path: Local filesystem directory for storage
            base_url: URL prefix for generated file URLs

        Creates the base directory if it doesn't exist.
        """
        self._base_path = base_path
        self._base_url = base_url.rstrip("/")
        self._base_path.mkdir(parents=True, exist_ok=True)

    @property
    def base_path(self) -> Path:
        """Get the base storage path."""
        return self._base_path

    @property
    def base_url(self) -> str:
        """Get the base URL prefix."""
        return self._base_url

    async def upload(self, file: UploadFile, path: str) -> str:
        """Upload file to local filesystem."""
        full_path = self._resolve_path(path)
        self._ensure_parent_exists(full_path)

        content = await file.read()
        full_path.write_bytes(content)

        return self._build_url(path)

    async def delete(self, path: str) -> bool:
        """Delete file from local filesystem."""
        full_path = self._resolve_path(path)

        if full_path.exists():
            full_path.unlink()
            return True

        return False

    def _resolve_path(self, relative_path: str) -> Path:
        """Resolve relative path to absolute filesystem path."""
        return self._base_path / relative_path

    def _ensure_parent_exists(self, path: Path) -> None:
        """Create parent directories if they don't exist."""
        path.parent.mkdir(parents=True, exist_ok=True)

    def _build_url(self, path: str) -> str:
        """Build public URL for uploaded file."""
        return f"{self._base_url}/{path}"

