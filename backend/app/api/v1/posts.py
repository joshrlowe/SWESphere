"""
Post API routes.

Endpoints for creating, reading, updating, deleting posts,
as well as feeds, likes, and replies.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, OptionalUser
from app.dependencies import NotificationSvc, PostSvc
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostCreate, PostResponse, PostUpdate

router = APIRouter()


# =============================================================================
# Response Building Helpers
# =============================================================================

async def _build_post_response(
    post: Post,
    post_service: PostSvc,
    current_user: User | None = None,
) -> PostResponse:
    """
    Build a PostResponse with computed fields like is_liked.
    
    Args:
        post: Post model to convert
        post_service: Service for checking like status
        current_user: Current user (optional) for personalization
        
    Returns:
        PostResponse with all computed fields populated
    """
    response = PostResponse.model_validate(post)
    
    if current_user:
        response.is_liked = await post_service.is_liked(current_user.id, post.id)
    else:
        response.is_liked = False
    
    return response


async def _build_post_list_response(
    posts: list[Post],
    post_service: PostSvc,
    current_user: User | None = None,
) -> list[PostResponse]:
    """
    Build a list of PostResponses with computed fields.
    
    Args:
        posts: List of Post models
        post_service: Service for checking like status
        current_user: Current user (optional) for personalization
        
    Returns:
        List of PostResponses
    """
    return [
        await _build_post_response(post, post_service, current_user)
        for post in posts
    ]


# =============================================================================
# Post CRUD Endpoints
# =============================================================================

@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new post",
)
async def create_post(
    data: PostCreate,
    current_user: CurrentUser,
    post_service: PostSvc,
) -> PostResponse:
    """
    Create a new post (tweet).

    - **body**: Post content (1-280 characters)
    - **media_url**: Optional media attachment URL
    - **reply_to_id**: Optional ID of post being replied to
    """
    post = await post_service.create_post(current_user.id, data)
    return await _build_post_response(post, post_service, current_user)


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Get a post",
)
async def get_post(
    post_id: int,
    post_service: PostSvc,
    current_user: OptionalUser = None,
) -> PostResponse:
    """Get a specific post by ID."""
    post = await post_service.get_post(post_id)
    return await _build_post_response(post, post_service, current_user)


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
    summary="Update a post",
)
async def update_post(
    post_id: int,
    data: PostUpdate,
    current_user: CurrentUser,
    post_service: PostSvc,
) -> PostResponse:
    """Update a post. Only the author can update their posts."""
    post = await post_service.update_post(post_id, current_user.id, data)
    return await _build_post_response(post, post_service, current_user)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post",
)
async def delete_post(
    post_id: int,
    current_user: CurrentUser,
    post_service: PostSvc,
) -> None:
    """Delete a post. Only the author can delete their posts."""
    await post_service.delete_post(post_id, current_user.id)


# =============================================================================
# Feed & Discovery Endpoints
# =============================================================================

@router.get(
    "/feed",
    response_model=list[PostResponse],
    summary="Get personalized feed",
)
async def get_feed(
    current_user: CurrentUser,
    post_service: PostSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[PostResponse]:
    """Get posts from users you follow and your own posts."""
    posts = await post_service.get_feed(current_user.id, skip=skip, limit=limit)
    return await _build_post_list_response(posts, post_service, current_user)


@router.get(
    "/explore",
    response_model=list[PostResponse],
    summary="Get explore posts",
)
async def get_explore(
    post_service: PostSvc,
    current_user: OptionalUser = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[PostResponse]:
    """Get all recent posts for exploration (public endpoint)."""
    posts = await post_service.get_explore(skip=skip, limit=limit)
    return await _build_post_list_response(posts, post_service, current_user)


@router.get(
    "/search",
    response_model=list[PostResponse],
    summary="Search posts",
)
async def search_posts(
    q: str = Query(..., min_length=1),
    post_service: PostSvc = ...,
    current_user: OptionalUser = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[PostResponse]:
    """Search posts by content."""
    posts = await post_service.search_posts(q, skip=skip, limit=limit)
    return await _build_post_list_response(posts, post_service, current_user)


@router.get(
    "/{post_id}/replies",
    response_model=list[PostResponse],
    summary="Get replies to a post",
)
async def get_replies(
    post_id: int,
    post_service: PostSvc,
    current_user: OptionalUser = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[PostResponse]:
    """Get replies to a specific post."""
    posts = await post_service.get_replies(post_id, skip=skip, limit=limit)
    return await _build_post_list_response(posts, post_service, current_user)


# =============================================================================
# Like Endpoints
# =============================================================================

@router.post(
    "/{post_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Like a post",
)
async def like_post(
    post_id: int,
    current_user: CurrentUser,
    post_service: PostSvc,
    notification_service: NotificationSvc,
) -> None:
    """Like a post."""
    post = await post_service.get_post(post_id)
    liked = await post_service.like_post(current_user.id, post_id)

    # Notify post author (unless liking own post)
    if liked and post.user_id != current_user.id:
        await notification_service.notify_post_liked(
            user_id=post.user_id,
            liker_id=current_user.id,
            liker_username=current_user.username,
            post_id=post_id,
        )


@router.delete(
    "/{post_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlike a post",
)
async def unlike_post(
    post_id: int,
    current_user: CurrentUser,
    post_service: PostSvc,
) -> None:
    """Remove like from a post."""
    await post_service.unlike_post(current_user.id, post_id)
