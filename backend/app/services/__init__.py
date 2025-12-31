"""
Service layer for business logic.

Services handle:
- Business rules and validation
- Coordination between repositories
- External service integration
- Caching logic (with Redis)
- Real-time notifications
- File storage

Architecture:
- Services orchestrate business logic
- Repositories handle data access
- Storage handles file operations
- Exceptions provide domain-specific errors
"""

from app.core.pagination import PaginatedResult
from app.services.auth_service import AuthService
from app.services.avatar_service import AvatarConfig, AvatarService
from app.services.cache_invalidation import CacheInvalidator
from app.services.cache_service import CacheService
from app.services.exceptions import (
    CannotFollowSelfError,
    ContentTooLongError,
    EmptyContentError,
    InvalidAvatarError,
    PasswordMismatchError,
    PostNotFoundError,
    ServiceError,
    UnauthorizedPostActionError,
    UserNotFoundError,
    UsernameConflictError,
)
from app.services.notification_service import (
    NotificationService,
    PaginatedNotifications,
)
from app.services.post_service import PostService
from app.services.realtime_service import RealtimeService, realtime_service
from app.services.recommendation_service import (
    RecommendationService,
    ScoredPost,
    get_recommendation_service,
)
from app.services.moderation_service import (
    ModerationService,
    get_moderation_service,
)
from app.services.storage import FileStorage, LocalFileStorage
from app.services.user_service import UserService

__all__ = [
    # Core Services
    "AuthService",
    "UserService",
    "PostService",
    "NotificationService",
    "RealtimeService",
    "realtime_service",
    # Recommendation Service
    "RecommendationService",
    "ScoredPost",
    "get_recommendation_service",
    # Moderation Service
    "ModerationService",
    "get_moderation_service",
    # Avatar Service
    "AvatarService",
    "AvatarConfig",
    # Cache Services
    "CacheService",
    "CacheInvalidator",
    # Storage
    "FileStorage",
    "LocalFileStorage",
    # Exceptions
    "ServiceError",
    "UserNotFoundError",
    "UsernameConflictError",
    "PasswordMismatchError",
    "CannotFollowSelfError",
    "InvalidAvatarError",
    "PostNotFoundError",
    "UnauthorizedPostActionError",
    "EmptyContentError",
    "ContentTooLongError",
    # Pagination
    "PaginatedResult",
    "PaginatedNotifications",
]
