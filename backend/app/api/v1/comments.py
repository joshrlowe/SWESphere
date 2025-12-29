"""Comment routes."""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser
from app.dependencies import DBSession, NotificationSvc, PostSvc
from app.models.comment import Comment
from app.schemas.post import CommentCreate, CommentResponse

router = APIRouter()


@router.post(
    "/posts/{post_id}",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to post",
)
async def create_comment(
    post_id: int,
    data: CommentCreate,
    current_user: CurrentUser,
    db: DBSession,
    post_service: PostSvc,
    notification_service: NotificationSvc,
) -> CommentResponse:
    """
    Add a comment to a post.
    """
    # Verify post exists
    post = await post_service.get_post(post_id)

    # Create comment
    comment = Comment(
        body=data.body,
        author_id=current_user.id,
        post_id=post_id,
        parent_id=data.parent_id,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment, ["author"])

    # Send notification if commenting on someone else's post
    if post.author_id != current_user.id:
        await notification_service.notify_new_comment(
            user_id=post.author_id,
            commenter_id=current_user.id,
            commenter_username=current_user.username,
            post_id=post_id,
        )

    return CommentResponse.model_validate(comment)


@router.get(
    "/posts/{post_id}",
    response_model=list[CommentResponse],
    summary="Get comments for post",
)
async def get_post_comments(
    post_id: int,
    db: DBSession,
    post_service: PostSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[CommentResponse]:
    """
    Get all comments for a post.
    """
    # Verify post exists
    await post_service.get_post(post_id)

    result = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id, Comment.parent_id.is_(None))
        .options(selectinload(Comment.author))
        .order_by(Comment.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    comments = result.scalars().all()

    return [CommentResponse.model_validate(c) for c in comments]


@router.get(
    "/{comment_id}",
    response_model=CommentResponse,
    summary="Get a comment",
)
async def get_comment(
    comment_id: int,
    db: DBSession,
) -> CommentResponse:
    """
    Get a specific comment by ID.
    """
    result = await db.execute(
        select(Comment)
        .where(Comment.id == comment_id)
        .options(selectinload(Comment.author))
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    return CommentResponse.model_validate(comment)


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
)
async def delete_comment(
    comment_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """
    Delete a comment. Only the author can delete their comments.
    """
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment",
        )

    await db.delete(comment)
    await db.flush()


@router.get(
    "/{comment_id}/replies",
    response_model=list[CommentResponse],
    summary="Get replies to a comment",
)
async def get_comment_replies(
    comment_id: int,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[CommentResponse]:
    """
    Get replies to a specific comment.
    """
    result = await db.execute(
        select(Comment)
        .where(Comment.parent_id == comment_id)
        .options(selectinload(Comment.author))
        .order_by(Comment.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    comments = result.scalars().all()

    return [CommentResponse.model_validate(c) for c in comments]
