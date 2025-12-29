"""
User routes.

Endpoints for user profiles, following, and search.
"""

from fastapi import APIRouter, File, Query, UploadFile, status

from app.api.deps import CurrentUser, OptionalUser
from app.dependencies import NotificationSvc, UserSvc
from app.schemas.common import MessageResponse
from app.schemas.user import (
    UserListResponse,
    UserPublic,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


# =============================================================================
# Current User Profile
# =============================================================================


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    responses={
        200: {"description": "Current user profile"},
        401: {"description": "Not authenticated"},
    },
)
async def get_current_user_profile(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get the authenticated user's full profile.

    Returns complete user information including email and account settings.
    """
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    responses={
        200: {"description": "Profile updated successfully"},
        400: {"description": "Username already taken"},
        401: {"description": "Not authenticated"},
    },
)
async def update_current_user_profile(
    data: UserUpdate,
    current_user: CurrentUser,
    user_service: UserSvc,
) -> UserResponse:
    """
    Update the current user's profile information.

    - **username**: Optional new username (must be unique)
    - **display_name**: Optional display name
    - **bio**: Optional biography (max 500 chars)
    - **location**: Optional location
    - **website**: Optional website URL
    """
    user = await user_service.update_profile(current_user.id, data)
    return UserResponse.model_validate(user)


@router.post(
    "/me/avatar",
    response_model=UserResponse,
    summary="Upload avatar",
    responses={
        200: {"description": "Avatar uploaded successfully"},
        400: {"description": "Invalid file type or size"},
        401: {"description": "Not authenticated"},
    },
)
async def upload_avatar(
    current_user: CurrentUser,
    user_service: UserSvc,
    file: UploadFile = File(..., description="Avatar image file (JPEG, PNG, GIF, WebP)"),
) -> UserResponse:
    """
    Upload a new avatar image for the current user.

    Supported formats: JPEG, PNG, GIF, WebP
    Maximum file size: 2MB
    Images will be resized to a square format.
    """
    user = await user_service.upload_avatar(current_user.id, file)
    return UserResponse.model_validate(user)


@router.delete(
    "/me/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove avatar",
    responses={
        204: {"description": "Avatar removed successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def remove_avatar(
    current_user: CurrentUser,
    user_service: UserSvc,
) -> None:
    """Remove the current user's avatar, reverting to the default."""
    await user_service.remove_avatar(current_user.id)


# =============================================================================
# User Search
# =============================================================================


@router.get(
    "/search",
    response_model=UserListResponse,
    summary="Search users",
    responses={200: {"description": "Search results"}},
)
async def search_users(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    user_service: UserSvc = ...,
) -> UserListResponse:
    """
    Search for users by username or display name.

    Returns paginated results sorted by relevance.
    """
    result = await user_service.search_users(q, page=page, per_page=per_page)
    return UserListResponse.create(
        users=result.users,
        total=result.total,
        page=page,
        per_page=per_page,
    )


# =============================================================================
# User Profiles
# =============================================================================


@router.get(
    "/{username}",
    response_model=UserPublic,
    summary="Get user profile",
    responses={
        200: {"description": "User profile"},
        404: {"description": "User not found"},
    },
)
async def get_user_profile(
    username: str,
    user_service: UserSvc,
    current_user: OptionalUser = None,
) -> UserPublic:
    """
    Get a user's public profile by username.

    Returns public information visible to all users.
    """
    user = await user_service.get_user_by_username(username)
    
    # Compute is_following status for authenticated users
    is_following = None
    if current_user and current_user.id != user.id:
        is_following = await user_service.is_following(current_user.id, user.id)

    return UserPublic.from_model(user, is_following=is_following)


# =============================================================================
# Following & Followers
# =============================================================================


@router.post(
    "/{username}/follow",
    response_model=MessageResponse,
    summary="Follow a user",
    responses={
        200: {"description": "Followed successfully"},
        400: {"description": "Cannot follow yourself or already following"},
        404: {"description": "User not found"},
    },
)
async def follow_user(
    username: str,
    current_user: CurrentUser,
    user_service: UserSvc,
    notification_service: NotificationSvc,
) -> MessageResponse:
    """
    Follow another user.

    You will see their posts in your home feed.
    """
    target_user = await user_service.get_user_by_username(username)
    followed = await user_service.follow_user(current_user.id, target_user.id)

    if followed:
        await notification_service.notify_new_follower(
            user_id=target_user.id,
            follower_id=current_user.id,
            follower_username=current_user.username,
        )
        return MessageResponse(message=f"You are now following @{username}")

    return MessageResponse(message=f"You are already following @{username}")


@router.delete(
    "/{username}/follow",
    response_model=MessageResponse,
    summary="Unfollow a user",
    responses={
        200: {"description": "Unfollowed successfully"},
        404: {"description": "User not found"},
    },
)
async def unfollow_user(
    username: str,
    current_user: CurrentUser,
    user_service: UserSvc,
) -> MessageResponse:
    """
    Unfollow a user.

    Their posts will no longer appear in your home feed.
    """
    target_user = await user_service.get_user_by_username(username)
    await user_service.unfollow_user(current_user.id, target_user.id)
    return MessageResponse(message=f"You have unfollowed @{username}")


@router.get(
    "/{username}/followers",
    response_model=UserListResponse,
    summary="Get user's followers",
    responses={
        200: {"description": "List of followers"},
        404: {"description": "User not found"},
    },
)
async def get_followers(
    username: str,
    user_service: UserSvc,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
) -> UserListResponse:
    """Get a paginated list of users following this user."""
    user = await user_service.get_user_by_username(username)
    result = await user_service.get_followers(user.id, page=page, per_page=per_page)
    return UserListResponse.create(
        users=result.users,
        total=result.total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{username}/following",
    response_model=UserListResponse,
    summary="Get users this user follows",
    responses={
        200: {"description": "List of followed users"},
        404: {"description": "User not found"},
    },
)
async def get_following(
    username: str,
    user_service: UserSvc,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
) -> UserListResponse:
    """Get a paginated list of users this user is following."""
    user = await user_service.get_user_by_username(username)
    result = await user_service.get_following(user.id, page=page, per_page=per_page)
    return UserListResponse.create(
        users=result.users,
        total=result.total,
        page=page,
        per_page=per_page,
    )
