"""
Tests for AvatarService.

Covers:
- Avatar upload with validation
- File type validation
- File size validation
- Avatar deletion
- Avatar replacement
- Filename generation
"""

import pytest
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

from fastapi import UploadFile

from app.services.avatar_service import AvatarConfig, AvatarService
from app.services.exceptions import AvatarTooLargeError, InvalidAvatarTypeError


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def avatar_config():
    """Create test avatar configuration."""
    return AvatarConfig(
        allowed_types=frozenset(["image/jpeg", "image/png"]),
        max_size_bytes=1024 * 1024,  # 1MB
        storage_path_prefix="/uploads/avatars",
    )


@pytest.fixture
def mock_storage():
    """Create mock file storage."""
    storage = AsyncMock()
    storage.upload = AsyncMock(return_value="/uploads/avatars/123/test-uuid.jpg")
    storage.delete = AsyncMock(return_value=True)
    return storage


@pytest.fixture
def avatar_service(mock_storage, avatar_config):
    """Create AvatarService with mocks."""
    return AvatarService(storage=mock_storage, config=avatar_config)


def create_upload_file(
    content: bytes = b"fake image content",
    filename: str = "test.jpg",
    content_type: str = "image/jpeg",
) -> UploadFile:
    """Create a mock UploadFile."""
    file = MagicMock(spec=UploadFile)
    file.filename = filename
    file.content_type = content_type
    file.read = AsyncMock(return_value=content)
    file.seek = AsyncMock()
    return file


# =============================================================================
# AvatarConfig Tests
# =============================================================================


class TestAvatarConfig:
    """Tests for AvatarConfig."""

    def test_from_settings(self):
        """Should create config from settings."""
        config = AvatarConfig.from_settings()
        
        assert config.max_size_bytes > 0
        assert len(config.allowed_types) > 0

    def test_max_size_mb(self, avatar_config):
        """Should calculate max size in MB."""
        assert avatar_config.max_size_mb == 1.0

    def test_allowed_types_display(self, avatar_config):
        """Should format allowed types for display."""
        display = avatar_config.allowed_types_display
        
        assert "image/jpeg" in display
        assert "image/png" in display

    def test_is_valid_type_true(self, avatar_config):
        """Should return True for valid type."""
        assert avatar_config.is_valid_type("image/jpeg") is True
        assert avatar_config.is_valid_type("image/png") is True

    def test_is_valid_type_false(self, avatar_config):
        """Should return False for invalid type."""
        assert avatar_config.is_valid_type("image/gif") is False
        assert avatar_config.is_valid_type("text/plain") is False
        assert avatar_config.is_valid_type(None) is False


# =============================================================================
# Upload Tests
# =============================================================================


class TestAvatarUpload:
    """Tests for avatar upload."""

    @pytest.mark.asyncio
    async def test_upload_success(self, avatar_service, mock_storage):
        """Should upload valid avatar."""
        file = create_upload_file()
        
        url = await avatar_service.upload(user_id=123, file=file)
        
        assert url == "/uploads/avatars/123/test-uuid.jpg"
        mock_storage.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_invalid_type_raises(self, avatar_service):
        """Should raise for invalid file type."""
        file = create_upload_file(content_type="image/gif")
        
        with pytest.raises(InvalidAvatarTypeError):
            await avatar_service.upload(user_id=123, file=file)

    @pytest.mark.asyncio
    async def test_upload_too_large_raises(self, avatar_service):
        """Should raise for file exceeding size limit."""
        large_content = b"x" * (1024 * 1024 + 1)  # 1MB + 1 byte
        file = create_upload_file(content=large_content)
        
        with pytest.raises(AvatarTooLargeError):
            await avatar_service.upload(user_id=123, file=file)

    @pytest.mark.asyncio
    async def test_upload_resets_file_position(self, avatar_service):
        """Should reset file position after size check."""
        file = create_upload_file()
        
        await avatar_service.upload(user_id=123, file=file)
        
        file.seek.assert_called_with(0)


# =============================================================================
# Delete Tests
# =============================================================================


class TestAvatarDelete:
    """Tests for avatar deletion."""

    @pytest.mark.asyncio
    async def test_delete_success(self, avatar_service, mock_storage):
        """Should delete avatar by URL."""
        url = "/uploads/avatars/123/uuid.jpg"
        
        result = await avatar_service.delete(url)
        
        assert result is True
        mock_storage.delete.assert_called_once_with("123/uuid.jpg")

    @pytest.mark.asyncio
    async def test_delete_not_found(self, avatar_service, mock_storage):
        """Should return False when avatar not found."""
        mock_storage.delete = AsyncMock(return_value=False)
        
        result = await avatar_service.delete("/uploads/avatars/999/missing.jpg")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_for_user_with_avatar(self, avatar_service, mock_storage):
        """Should delete user's avatar."""
        user = MagicMock()
        user.avatar_url = "/uploads/avatars/123/avatar.jpg"
        
        await avatar_service.delete_for_user(user)
        
        mock_storage.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_for_user_without_avatar(self, avatar_service, mock_storage):
        """Should do nothing if user has no avatar."""
        user = MagicMock()
        user.avatar_url = None
        
        await avatar_service.delete_for_user(user)
        
        mock_storage.delete.assert_not_called()


# =============================================================================
# Replace Tests
# =============================================================================


class TestAvatarReplace:
    """Tests for avatar replacement."""

    @pytest.mark.asyncio
    async def test_replace_deletes_old_and_uploads_new(
        self, avatar_service, mock_storage
    ):
        """Should delete old avatar and upload new one."""
        file = create_upload_file()
        old_url = "/uploads/avatars/123/old.jpg"
        
        new_url = await avatar_service.replace(
            user_id=123,
            new_file=file,
            old_avatar_url=old_url,
        )
        
        # Should delete old
        mock_storage.delete.assert_called_once()
        # Should upload new
        mock_storage.upload.assert_called_once()
        assert new_url is not None

    @pytest.mark.asyncio
    async def test_replace_without_old_avatar(self, avatar_service, mock_storage):
        """Should just upload when no old avatar."""
        file = create_upload_file()
        
        await avatar_service.replace(
            user_id=123,
            new_file=file,
            old_avatar_url=None,
        )
        
        mock_storage.delete.assert_not_called()
        mock_storage.upload.assert_called_once()


# =============================================================================
# Filename Generation Tests
# =============================================================================


class TestFilenameGeneration:
    """Tests for filename generation."""

    def test_generate_filename_with_extension(self, avatar_service):
        """Should preserve file extension."""
        filename = avatar_service._generate_filename(123, "photo.png")
        
        assert filename.startswith("123/")
        assert filename.endswith(".png")

    def test_generate_filename_without_extension(self, avatar_service):
        """Should default to jpg when no extension."""
        filename = avatar_service._generate_filename(123, "photo")
        
        assert filename.endswith(".jpg")

    def test_generate_filename_with_none(self, avatar_service):
        """Should default to jpg when filename is None."""
        filename = avatar_service._generate_filename(123, None)
        
        assert filename.endswith(".jpg")

    def test_generate_filename_is_unique(self, avatar_service):
        """Should generate unique filenames."""
        filename1 = avatar_service._generate_filename(123, "photo.jpg")
        filename2 = avatar_service._generate_filename(123, "photo.jpg")
        
        assert filename1 != filename2

    def test_extract_extension_from_dotted_filename(self, avatar_service):
        """Should extract extension from filename with dot."""
        assert avatar_service._extract_extension("photo.jpg") == "jpg"
        assert avatar_service._extract_extension("my.file.png") == "png"
        assert avatar_service._extract_extension("IMAGE.JPEG") == "jpeg"


# =============================================================================
# URL Path Extraction Tests
# =============================================================================


class TestPathExtraction:
    """Tests for extracting storage path from URL."""

    def test_extract_path_standard_url(self, avatar_service):
        """Should extract path from standard URL."""
        url = "/uploads/avatars/123/uuid.jpg"
        
        path = avatar_service._extract_path_from_url(url)
        
        assert path == "123/uuid.jpg"

    def test_extract_path_fallback(self, avatar_service):
        """Should fallback to filename when pattern not found."""
        url = "/other/path/file.jpg"
        
        path = avatar_service._extract_path_from_url(url)
        
        assert path == "file.jpg"

