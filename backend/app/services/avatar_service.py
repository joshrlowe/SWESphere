"""
Avatar management service.

Handles avatar uploads, validation, and deletion with:
- File type validation (configurable allowed types)
- File size validation (configurable max size)
- Unique filename generation with UUID
- Integration with pluggable storage backends

This service is extracted from UserService following
Single Responsibility Principle.
"""

from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings
from app.services.exceptions import AvatarTooLargeError, InvalidAvatarTypeError
from app.services.storage import FileStorage, LocalFileStorage

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_EXTENSION = "jpg"
BYTES_PER_MB = 1024 * 1024


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class AvatarConfig:
    """
    Immutable configuration for avatar uploads.

    Attributes:
        allowed_types: Set of allowed MIME types
        max_size_bytes: Maximum file size in bytes
        storage_path_prefix: URL path prefix for stored avatars
    """

    allowed_types: frozenset[str]
    max_size_bytes: int
    storage_path_prefix: str

    @classmethod
    def from_settings(cls) -> "AvatarConfig":
        """Create configuration from application settings."""
        return cls(
            allowed_types=frozenset(settings.ALLOWED_IMAGE_TYPES),
            max_size_bytes=settings.AVATAR_MAX_SIZE,
            storage_path_prefix="/uploads/avatars",
        )

    @property
    def max_size_mb(self) -> float:
        """Maximum file size in megabytes."""
        return self.max_size_bytes / BYTES_PER_MB

    @property
    def allowed_types_display(self) -> str:
        """Human-readable list of allowed types."""
        return ", ".join(sorted(self.allowed_types))

    def is_valid_type(self, content_type: str | None) -> bool:
        """Check if content type is allowed."""
        return content_type in self.allowed_types


# =============================================================================
# Service
# =============================================================================


class AvatarService:
    """
    Service for avatar upload and management.

    Responsibilities:
    - Validate avatar files (type, size)
    - Generate unique filenames
    - Upload to storage backend
    - Delete old avatars

    This class is stateless except for injected dependencies.
    """

    def __init__(
        self,
        storage: FileStorage | None = None,
        config: AvatarConfig | None = None,
    ) -> None:
        """
        Initialize avatar service.

        Args:
            storage: File storage backend (defaults to local storage)
            config: Avatar configuration (defaults to settings-based config)
        """
        self._config = config or AvatarConfig.from_settings()
        self._storage = storage or self._create_default_storage()

    @staticmethod
    def _create_default_storage() -> LocalFileStorage:
        """Create default local file storage."""
        return LocalFileStorage(
            base_path=Path("./uploads/avatars"),
            base_url="/uploads/avatars",
        )

    # =========================================================================
    # Public API
    # =========================================================================

    async def upload(self, user_id: int, file: UploadFile) -> str:
        """
        Upload a new avatar for a user.

        Validates the file and stores it with a unique filename.

        Args:
            user_id: Owner user ID (used for path organization)
            file: Uploaded image file

        Returns:
            URL of the uploaded avatar

        Raises:
            InvalidAvatarTypeError: If file type not allowed
            AvatarTooLargeError: If file exceeds size limit
        """
        await self._validate(file)
        filename = self._generate_filename(user_id, file.filename)
        url = await self._storage.upload(file, filename)

        logger.info("Avatar uploaded: user_id=%d, url=%s", user_id, url)
        return url

    async def delete(self, avatar_url: str) -> bool:
        """
        Delete an avatar by URL.

        Args:
            avatar_url: Full URL of the avatar to delete

        Returns:
            True if deleted, False if not found
        """
        path = self._extract_path_from_url(avatar_url)
        deleted = await self._storage.delete(path)

        if deleted:
            logger.info("Avatar deleted: %s", avatar_url)

        return deleted

    async def replace(
        self,
        user_id: int,
        new_file: UploadFile,
        old_avatar_url: str | None,
    ) -> str:
        """
        Replace user's avatar, deleting the old one if present.

        Args:
            user_id: Owner user ID
            new_file: New avatar file
            old_avatar_url: URL of current avatar to delete

        Returns:
            URL of the new avatar
        """
        if old_avatar_url:
            await self.delete(old_avatar_url)

        return await self.upload(user_id, new_file)

    async def delete_for_user(self, user: "User") -> None:
        """
        Delete avatar for a user if they have one.

        Args:
            user: User whose avatar to delete
        """
        if user.avatar_url:
            await self.delete(user.avatar_url)

    # =========================================================================
    # Validation
    # =========================================================================

    async def _validate(self, file: UploadFile) -> None:
        """
        Validate avatar file type and size.

        Raises appropriate exceptions on validation failure.
        """
        self._validate_content_type(file)
        await self._validate_size(file)

    def _validate_content_type(self, file: UploadFile) -> None:
        """Validate file content type."""
        if not self._config.is_valid_type(file.content_type):
            raise InvalidAvatarTypeError(self._config.allowed_types_display)

    async def _validate_size(self, file: UploadFile) -> None:
        """Validate file size by reading content."""
        content = await file.read()
        await file.seek(0)  # Reset for subsequent read

        if len(content) > self._config.max_size_bytes:
            raise AvatarTooLargeError(self._config.max_size_mb)

    # =========================================================================
    # Filename Generation
    # =========================================================================

    def _generate_filename(
        self,
        user_id: int,
        original_filename: str | None,
    ) -> str:
        """
        Generate unique filename for avatar.

        Pattern: {user_id}/{uuid}.{extension}

        This ensures:
        - User avatars are organized by user ID
        - Filenames are unique (UUID)
        - Original extension is preserved when possible
        """
        extension = self._extract_extension(original_filename)
        unique_id = uuid4()
        return f"{user_id}/{unique_id}.{extension}"

    @staticmethod
    def _extract_extension(filename: str | None) -> str:
        """
        Extract file extension from filename.

        Falls back to 'jpg' if extension cannot be determined.
        """
        if not filename:
            return DEFAULT_EXTENSION

        # Try direct extraction from filename
        if "." in filename:
            return filename.rsplit(".", 1)[-1].lower()

        # Try guessing from MIME type
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type:
            extension = mimetypes.guess_extension(guessed_type)
            if extension:
                return extension.lstrip(".")

        return DEFAULT_EXTENSION

    def _extract_path_from_url(self, url: str) -> str:
        """
        Extract storage path from avatar URL.

        Handles URLs like "/uploads/avatars/123/uuid.jpg"
        and extracts "123/uuid.jpg".
        """
        marker = f"{self._config.storage_path_prefix}/"
        if marker in url:
            return url.split(marker)[-1]

        # Fallback: return everything after the last slash
        return url.rsplit("/", 1)[-1]

