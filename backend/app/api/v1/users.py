"""User routes."""

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser
from app.dependencies import NotificationSvc, UserSvc
from app.schemas.user import UserPublic, UserResponse, UserUpdate

router = APIRouter()


@router.get(
    "/{username}",
    response_model=UserPublic,
    summary="Get user profile",
)
async def get_user(
    username: str,
    user_service: UserSvc,
) -> UserPublic:
    """
    Get a user's public profile by username.
    """
    user = await user_service.get_user_by_username(username)
    return UserPublic.model_validate(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user's profile",
)
async def update_profile(
    data: UserUpdate,
    current_user: CurrentUser,
    user_service: UserSvc,
) -> UserResponse:
    """
    Update the current user's profile information.
    """
    user = await user_service.update_profile(current_user.id, data)
    return UserResponse.model_validate(user)


@router.post(
    "/{username}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Follow a user",
)
async def follow_user(
    username: str,
    current_user: CurrentUser,
    user_service: UserSvc,
    notification_service: NotificationSvc,
) -> None:
    """
    Follow another user.
    """
    target_user = await user_service.get_user_by_username(username)
    followed = await user_service.follow_user(current_user.id, target_user.id)

    if followed:
        # Send notification
        await notification_service.notify_new_follower(
            user_id=target_user.id,
            follower_id=current_user.id,
            follower_username=current_user.username,
        )


@router.delete(
    "/{username}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unfollow a user",
)
async def unfollow_user(
    username: str,
    current_user: CurrentUser,
    user_service: UserSvc,
) -> None:
    """
    Unfollow a user.
    """
    target_user = await user_service.get_user_by_username(username)
    await user_service.unfollow_user(current_user.id, target_user.id)


@router.get(
    "/{username}/followers",
    response_model=list[UserPublic],
    summary="Get user's followers",
)
async def get_followers(
    username: str,
    user_service: UserSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[UserPublic]:
    """
    Get a list of users following this user.
    """
    user = await user_service.get_user_by_username(username)
    followers = await user_service.get_followers(user.id, skip=skip, limit=limit)
    return [UserPublic.model_validate(f) for f in followers]


@router.get(
    "/{username}/following",
    response_model=list[UserPublic],
    summary="Get users this user follows",
)
async def get_following(
    username: str,
    user_service: UserSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[UserPublic]:
    """
    Get a list of users this user is following.
    """
    user = await user_service.get_user_by_username(username)
    following = await user_service.get_following(user.id, skip=skip, limit=limit)
    return [UserPublic.model_validate(f) for f in following]


@router.get(
    "/search/",
    response_model=list[UserPublic],
    summary="Search users",
)
async def search_users(
    q: str = Query(..., min_length=1),
    user_service: UserSvc = ...,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[UserPublic]:
    """
    Search for users by username or display name.
    """
    users = await user_service.search_users(q, skip=skip, limit=limit)
    return [UserPublic.model_validate(u) for u in users]

