"""
Service layer for business logic.

Services handle:
- Business rules and validation
- Coordination between repositories
- External service integration
- Caching logic
"""

from app.core.pagination import PaginatedResult
from app.services.auth_service import AuthService
from app.services.notification_service import (
    NotificationService,
    PaginatedNotifications,
)
from app.services.post_service import PostService
from app.services.user_service import UserService

__all__ = [
    # Services
    "AuthService",
    "UserService",
    "PostService",
    "NotificationService",
    # Pagination (consolidated)
    "PaginatedResult",
    "PaginatedNotifications",
]
