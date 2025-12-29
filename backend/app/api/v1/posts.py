"""
Post API routes.

Endpoints for creating, reading, updating, deleting posts,
as well as feeds, likes, comments, and replies.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, OptionalUser
from app.dependencies import NotificationSvc, PostSvc
from app.models.post import Post
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.post import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    PostCreate,
    PostDetailResponse,
    PostListResponse,
    PostResponse,
    PostUpdate,
)
from app.schemas.user import UserMinimal

router = APIRouter()


# =============================================================================
# Response Building
# =============================================================================


def _build_post_response_sync(
    post: Post,
    is_liked: bool = False,
) -> PostResponse:
    """
    Build a PostResponse from a Post model.
    
    This is the synchronous part that doesn't require database access.
    The is_liked field must be computed separately.
    """
    author = UserMinimal.from_model(post.author) if post.author else None
    replies_count = _get_replies_count(post)
    
    return PostResponse(
        id=post.id,
        body=post.body,
        media_url=post.media_url,
        media_type=post.media_type,
        author=author,
        reply_to_id=post.reply_to_id,
        repost_of_id=post.repost_of_id,
        likes_count=post.likes_count,
        comments_count=post.comments_count,
        replies_count=replies_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
        is_liked=is_liked,
    )


def _get_replies_count(post: Post) -> int:
    """
    Safely get replies count from a post.
    
    Avoids lazy-loading issues by checking if the relationship is loaded.
    """
    try:
        if hasattr(post, "_sa_instance_state") and "replies" in post.__dict__:
            return len(post.replies)
    except Exception:
        pass
    return 0


async def _build_post_response(
    post: Post,
    post_service: PostSvc,
    current_user: User | None = None,
) -> PostResponse:
    """
    Build a PostResponse with computed fields like is_liked.
    
    Async wrapper that fetches the like status for authenticated users.
    """
    is_liked = False
    if current_user:
        is_liked = await post_service.is_liked(current_user.id, post.id)
    
    return _build_post_response_sync(post, is_liked=is_liked)


async def _build_post_list(
    posts: list[Post],
    post_service: PostSvc,
    current_user: User | None = None,
) -> list[PostResponse]:
    """Build a list of PostResponses with computed fields."""
    return [
        await _build_post_response(post, post_service, current_user)
        for post in posts
    ]


def _create_post_list_response(
    posts: list[PostResponse],
    total: int,
    page: int,
    per_page: int,
) -> PostListResponse:
    """Create a paginated post list response."""
    return PostListResponse.create(
        posts=posts,
        total=total,
        page=page,
        per_page=per_page,
    )


# =============================================================================
# Feed & Discovery Endpoints
# =============================================================================


@router.get(
    "/feed",
    response_model=PostListResponse,
    summary="Get personalized feed",
    responses={
        200: {"description": "Home feed posts"},
        401: {"description": "Not authenticated"},
    },
)
async def get_feed(
    current_user: CurrentUser,
    post_service: PostSvc,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Posts per page"),
) -> PostListResponse:
    """
    Get posts from users you follow and your own posts.

    Posts are ordered by most recent first.
    Cached for performance with 5-minute TTL.
    """
    result = await post_service.get_home_feed(current_user.id, page=page, per_page=per_page)
    posts = await _build_post_list(result.posts, post_service, current_user)
    return _create_post_list_response(posts, result.total, page, per_page)


@router.get(
    "/explore",
    response_model=PostListResponse,
    summary="Get explore feed",
    responses={200: {"description": "Explore feed posts"}},
)
async def get_explore(
    post_service: PostSvc,
    current_user: OptionalUser = None,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Posts per page"),
) -> PostListResponse:
    """
    Get trending and recent posts for exploration.

    This is a public endpoint - no authentication required.
    Authenticated users will see personalized like status.
    """
    result = await post_service.get_explore_feed(page=page, per_page=per_page)
    posts = await _build_post_list(result.posts, post_service, current_user)
    return _create_post_list_response(posts, result.total, page, per_page)


@router.get(
    "/search",
    response_model=PostListResponse,
    summary="Search posts",
    responses={200: {"description": "Search results"}},
)
async def search_posts(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Posts per page"),
    post_service: PostSvc = ...,
    current_user: OptionalUser = None,
) -> PostListResponse:
    """
    Search posts by content.

    Returns posts matching the search query, ordered by relevance.
    """
    result = await post_service.search_posts(q, page=page, per_page=per_page)
    posts = await _build_post_list(result.posts, post_service, current_user)
    return _create_post_list_response(posts, result.total, page, per_page)


# =============================================================================
# Post CRUD Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new post",
    responses={
        201: {"description": "Post created successfully"},
        400: {"description": "Invalid post content"},
        401: {"description": "Not authenticated"},
    },
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

    Mentions (@username) will be automatically detected and notified.
    """
    post = await post_service.create_post(current_user.id, data)
    return await _build_post_response(post, post_service, current_user)


@router.get(
    "/{post_id}",
    response_model=PostDetailResponse,
    summary="Get a post with comments",
    responses={
        200: {"description": "Post details with comments"},
        404: {"description": "Post not found"},
    },
)
async def get_post(
    post_id: int,
    post_service: PostSvc,
    current_user: OptionalUser = None,
) -> PostDetailResponse:
    """
    Get a specific post by ID with its comments.

    Returns the post details along with the first page of comments.
    """
    post = await post_service.get_post(post_id)
    response = await _build_post_response(post, post_service, current_user)
    comments = await post_service.get_comments(post_id, page=1, per_page=20)

    return PostDetailResponse(
        **response.model_dump(),
        comments=[CommentResponse.model_validate(c) for c in comments.items],
        comments_total=comments.total,
    )


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
    summary="Update a post",
    responses={
        200: {"description": "Post updated successfully"},
        403: {"description": "Not authorized to edit this post"},
        404: {"description": "Post not found"},
    },
)
async def update_post(
    post_id: int,
    data: PostUpdate,
    current_user: CurrentUser,
    post_service: PostSvc,
) -> PostResponse:
    """
    Update a post's content.

    Only the author can update their posts.
    Updates are not allowed after 15 minutes of posting.
    """
    post = await post_service.update_post(post_id, current_user.id, data)
    return await _build_post_response(post, post_service, current_user)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post",
    responses={
        204: {"description": "Post deleted successfully"},
        403: {"description": "Not authorized to delete this post"},
        404: {"description": "Post not found"},
    },
)
async def delete_post(
    post_id: int,
    current_user: CurrentUser,
    post_service: PostSvc,
) -> None:
    """
    Delete a post.

    Only the author can delete their posts.
    This is a soft delete - the post is marked as deleted but not removed.
    """
    await post_service.delete_post(post_id, current_user.id)


# =============================================================================
# Post Replies
# =============================================================================


@router.get(
    "/{post_id}/replies",
    response_model=PostListResponse,
    summary="Get replies to a post",
    responses={
        200: {"description": "List of replies"},
        404: {"description": "Post not found"},
    },
)
async def get_replies(
    post_id: int,
    post_service: PostSvc,
    current_user: OptionalUser = None,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Replies per page"),
) -> PostListResponse:
    """
    Get replies to a specific post.

    Replies are ordered by most recent first.
    """
    result = await post_service.get_replies(post_id, page=page, per_page=per_page)
    posts = await _build_post_list(result.posts, post_service, current_user)
    return _create_post_list_response(posts, result.total, page, per_page)


# =============================================================================
# Likes
# =============================================================================


@router.post(
    "/{post_id}/like",
    response_model=MessageResponse,
    summary="Like a post",
    responses={
        200: {"description": "Post liked"},
        401: {"description": "Not authenticated"},
        404: {"description": "Post not found"},
    },
)
async def like_post(
    post_id: int,
    current_user: CurrentUser,
    post_service: PostSvc,
    notification_service: NotificationSvc,
) -> MessageResponse:
    """
    Like a post.

    The post author will be notified (unless liking your own post).
    """
    post = await post_service.get_post(post_id)
    liked = await post_service.like_post(current_user.id, post_id)

    if liked and post.user_id != current_user.id:
        await notification_service.notify_post_liked(
            user_id=post.user_id,
            liker_id=current_user.id,
            liker_username=current_user.username,
            post_id=post_id,
        )
        return MessageResponse(message="Post liked")

    return MessageResponse(message="Post already liked")


@router.delete(
    "/{post_id}/like",
    response_model=MessageResponse,
    summary="Unlike a post",
    responses={
        200: {"description": "Like removed"},
        401: {"description": "Not authenticated"},
        404: {"description": "Post not found"},
    },
)
async def unlike_post(
    post_id: int,
    current_user: CurrentUser,
    post_service: PostSvc,
) -> MessageResponse:
    """Remove a like from a post."""
    await post_service.unlike_post(current_user.id, post_id)
    return MessageResponse(message="Like removed")


# =============================================================================
# Comments
# =============================================================================


@router.get(
    "/{post_id}/comments",
    response_model=CommentListResponse,
    summary="Get post comments",
    responses={
        200: {"description": "List of comments"},
        404: {"description": "Post not found"},
    },
)
async def get_comments(
    post_id: int,
    post_service: PostSvc,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Comments per page"),
) -> CommentListResponse:
    """
    Get paginated comments for a post.

    Top-level comments are returned first, sorted by most recent.
    """
    result = await post_service.get_comments(post_id, page=page, per_page=per_page)
    return CommentListResponse.create(
        comments=result.items,
        total=result.total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment",
    responses={
        201: {"description": "Comment created"},
        400: {"description": "Invalid comment"},
        401: {"description": "Not authenticated"},
        404: {"description": "Post not found"},
    },
)
async def create_comment(
    post_id: int,
    data: CommentCreate,
    current_user: CurrentUser,
    post_service: PostSvc,
    notification_service: NotificationSvc,
) -> CommentResponse:
    """
    Add a comment to a post.

    - **body**: Comment content (1-500 characters)
    - **parent_id**: Optional parent comment ID for nested replies

    The post author will be notified of new comments.
    """
    comment = await post_service.create_comment(
        post_id=post_id,
        user_id=current_user.id,
        body=data.body,
        parent_id=data.parent_id,
    )

    # Notify post author (if not self-commenting)
    post = await post_service.get_post(post_id)
    if post.user_id != current_user.id:
        await notification_service.notify_new_comment(
            user_id=post.user_id,
            commenter_id=current_user.id,
            commenter_username=current_user.username,
            post_id=post_id,
            comment_preview=data.body[:50],
        )

    return CommentResponse.model_validate(comment)


@router.delete(
    "/{post_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
    responses={
        204: {"description": "Comment deleted"},
        403: {"description": "Not authorized to delete this comment"},
        404: {"description": "Comment not found"},
    },
)
async def delete_comment(
    post_id: int,
    comment_id: int,
    current_user: CurrentUser,
    post_service: PostSvc,
) -> None:
    """
    Delete a comment.

    Only the comment author or post author can delete comments.
    """
    await post_service.delete_comment(comment_id, current_user.id)


# =============================================================================
# User Posts
# =============================================================================


@router.get(
    "/user/{username}",
    response_model=PostListResponse,
    summary="Get user's posts",
    responses={
        200: {"description": "User's posts"},
        404: {"description": "User not found"},
    },
)
async def get_user_posts(
    username: str,
    post_service: PostSvc,
    current_user: OptionalUser = None,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Posts per page"),
    include_replies: bool = Query(False, description="Include reply posts"),
) -> PostListResponse:
    """
    Get posts by a specific user.

    By default, only original posts (not replies) are returned.
    Set include_replies=true to include reply posts.
    """
    result = await post_service.get_user_posts(
        username=username,
        page=page,
        per_page=per_page,
        include_replies=include_replies,
    )
    posts = await _build_post_list(result.posts, post_service, current_user)
    return _create_post_list_response(posts, result.total, page, per_page)
