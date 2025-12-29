"""
Post service.

Handles post creation, retrieval, updates, likes, and feed generation.
"""

from fastapi import HTTPException, status

from app.models.post import Post
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.post import PostCreate, PostUpdate


class PostService:
    """Service for post operations."""

    def __init__(
        self,
        post_repo: PostRepository,
        user_repo: UserRepository,
    ) -> None:
        self.post_repo = post_repo
        self.user_repo = user_repo

    # =========================================================================
    # Post CRUD
    # =========================================================================

    async def create_post(self, user_id: int, data: PostCreate) -> Post:
        """
        Create a new post.
        
        Args:
            user_id: Author's user ID
            data: Post content and metadata
            
        Returns:
            Created Post
            
        Raises:
            HTTPException: If reply_to post doesn't exist
        """
        if data.reply_to_id:
            await self._verify_post_exists(data.reply_to_id, "Post to reply to not found")

        return await self.post_repo.create(
            user_id=user_id,
            body=data.body,
            media_url=data.media_url,
            media_type=data.media_type,
            reply_to_id=data.reply_to_id,
        )

    async def get_post(self, post_id: int) -> Post:
        """
        Get a post by ID with author loaded.
        
        Args:
            post_id: Post ID to fetch
            
        Returns:
            Post with author relationship
            
        Raises:
            HTTPException: If post not found
        """
        post = await self.post_repo.get_with_author(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
        return post

    async def update_post(
        self,
        post_id: int,
        user_id: int,
        data: PostUpdate,
    ) -> Post:
        """
        Update a post.
        
        Args:
            post_id: Post to update
            user_id: User attempting the update (for authorization)
            data: Fields to update
            
        Returns:
            Updated Post
            
        Raises:
            HTTPException: If post not found or user not authorized
        """
        post = await self._get_authorized_post(post_id, user_id, "update")
        
        updated = await self.post_repo.update(
            post_id,
            **data.model_dump(exclude_unset=True),
        )
        return updated  # type: ignore[return-value]

    async def delete_post(self, post_id: int, user_id: int) -> bool:
        """
        Delete a post.
        
        Args:
            post_id: Post to delete
            user_id: User attempting the deletion (for authorization)
            
        Returns:
            True if deleted
            
        Raises:
            HTTPException: If post not found or user not authorized
        """
        await self._get_authorized_post(post_id, user_id, "delete")
        return await self.post_repo.delete(post_id)

    # =========================================================================
    # Feed & Discovery
    # =========================================================================

    async def get_feed(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Get personalized feed for a user (posts from followed users + own)."""
        return await self.post_repo.get_feed(user_id, skip=skip, limit=limit)

    async def get_explore(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Get public explore feed (all recent posts)."""
        return await self.post_repo.get_explore(skip=skip, limit=limit)

    async def get_user_posts(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Get all posts by a specific user."""
        return await self.post_repo.get_user_posts(user_id, skip=skip, limit=limit)

    async def get_replies(
        self,
        post_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Get replies to a specific post."""
        return await self.post_repo.get_replies(post_id, skip=skip, limit=limit)

    async def search_posts(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Search posts by content."""
        return await self.post_repo.search(query, skip=skip, limit=limit)

    # =========================================================================
    # Likes
    # =========================================================================

    async def like_post(self, user_id: int, post_id: int) -> bool:
        """
        Like a post.
        
        Args:
            user_id: User liking the post
            post_id: Post to like
            
        Returns:
            True if like was added (False if already liked)
            
        Raises:
            HTTPException: If post not found
        """
        await self._verify_post_exists(post_id)
        return await self.post_repo.like(user_id, post_id)

    async def unlike_post(self, user_id: int, post_id: int) -> bool:
        """
        Remove like from a post.
        
        Args:
            user_id: User unliking the post
            post_id: Post to unlike
            
        Returns:
            True if like was removed (False if wasn't liked)
        """
        return await self.post_repo.unlike(user_id, post_id)

    async def is_liked(self, user_id: int, post_id: int) -> bool:
        """Check if a user has liked a specific post."""
        return await self.post_repo.is_liked(user_id, post_id)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    async def _verify_post_exists(
        self,
        post_id: int,
        error_message: str = "Post not found",
    ) -> Post:
        """Verify a post exists, raising 404 if not."""
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_message,
            )
        return post

    async def _get_authorized_post(
        self,
        post_id: int,
        user_id: int,
        action: str,
    ) -> Post:
        """Get a post and verify the user is authorized to modify it."""
        post = await self._verify_post_exists(post_id)
        
        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to {action} this post",
            )
        
        return post
