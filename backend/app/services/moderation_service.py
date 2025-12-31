"""
Content moderation service.

Provides comprehensive content moderation including:
- Blocked word detection with word boundaries
- Spam pattern detection (repeated chars, excessive caps, URL/mention flooding)
- Optional external toxicity API integration
- Configurable thresholds and actions

Usage:
    service = ModerationService(db, redis)
    result = await service.moderate_post("content to check")
    if result.action == 'reject':
        raise ContentBlockedError(result.reason)
"""

import logging
import re
from typing import Optional, Sequence

import httpx
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blocked_word import BlockedWord
from app.schemas.moderation import (
    ModerationAction,
    ModerationResult,
    SpamCheckResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Spam detection thresholds
REPEATED_CHAR_THRESHOLD = 5  # "aaaaa" triggers
UPPERCASE_PERCENTAGE_THRESHOLD = 0.7  # 70% uppercase triggers
MAX_URLS_ALLOWED = 3
MAX_MENTIONS_ALLOWED = 10
MIN_CONTENT_LENGTH_FOR_CAPS_CHECK = 10  # Don't check caps on very short content

# Scoring thresholds for actions
SPAM_SCORE_REVIEW_THRESHOLD = 0.3  # Above this -> review
SPAM_SCORE_REJECT_THRESHOLD = 0.7  # Above this -> reject
TOXICITY_REVIEW_THRESHOLD = 0.5
TOXICITY_REJECT_THRESHOLD = 0.8

# Regex patterns
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"{}|\\^`\[\]]+" +
    r"|www\.[^\s<>\"{}|\\^`\[\]]+",
    re.IGNORECASE
)
MENTION_PATTERN = re.compile(r"@\w{1,64}", re.UNICODE)
REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{4,}", re.UNICODE)  # 5+ same chars

# Cache TTL for blocked words
BLOCKED_WORDS_CACHE_TTL = 300  # 5 minutes
BLOCKED_WORDS_CACHE_KEY = "moderation:blocked_words"


# =============================================================================
# Moderation Service
# =============================================================================


class ModerationService:
    """
    Service for content moderation.
    
    Provides methods to check content for:
    - Blocked words and phrases
    - Spam patterns
    - Toxicity (via external API)
    
    Example:
        service = ModerationService(db, redis)
        result = await service.moderate_post("Hello world!")
        
        if result.action == ModerationAction.REJECT:
            raise HTTPException(400, result.reason)
        elif result.action == ModerationAction.REVIEW:
            await queue_for_review(post_id)
    """
    
    def __init__(
        self,
        db: AsyncSession,
        redis: Optional[Redis] = None,
        toxicity_api_url: Optional[str] = None,
        toxicity_api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize moderation service.
        
        Args:
            db: Async database session
            redis: Optional Redis client for caching blocked words
            toxicity_api_url: Optional URL for external toxicity API
            toxicity_api_key: Optional API key for toxicity service
        """
        self.db = db
        self.redis = redis
        self.toxicity_api_url = toxicity_api_url
        self.toxicity_api_key = toxicity_api_key
        
        # In-memory cache fallback when Redis unavailable
        self._blocked_words_cache: list[BlockedWord] | None = None
    
    # =========================================================================
    # Main Moderation Method
    # =========================================================================
    
    async def moderate_post(self, content: str) -> ModerationResult:
        """
        Perform full moderation check on content.
        
        Combines all checks:
        1. Blocked words check (immediate reject for severe words)
        2. Spam pattern detection
        3. Optional toxicity API check
        
        Args:
            content: The content to moderate
            
        Returns:
            ModerationResult with action and details
        """
        if not content or not content.strip():
            return ModerationResult(
                approved=True,
                action=ModerationAction.APPROVE,
                reason="Empty content",
            )
        
        # Normalize content for checks
        normalized = content.strip()
        
        # Check blocked words
        flagged_words = await self.check_blocked_words(normalized)
        
        # Check spam patterns
        spam_result = self.check_spam_patterns(normalized)
        
        # Optional toxicity check
        toxicity_score: Optional[float] = None
        if self.toxicity_api_url:
            try:
                toxicity_score = await self.check_toxicity(normalized)
            except Exception as e:
                logger.warning(f"Toxicity API failed: {e}")
        
        # Determine action based on results
        action, reason = self._determine_action(
            flagged_words=flagged_words,
            spam_result=spam_result,
            toxicity_score=toxicity_score,
        )
        
        return ModerationResult(
            approved=(action == ModerationAction.APPROVE),
            flagged_words=flagged_words,
            spam_score=spam_result.score,
            toxicity_score=toxicity_score,
            action=action,
            reason=reason,
        )
    
    # =========================================================================
    # Blocked Words Check
    # =========================================================================
    
    async def check_blocked_words(self, content: str) -> list[str]:
        """
        Check content for blocked words.
        
        Uses word boundary matching to avoid false positives
        (e.g., "class" won't match "ass").
        
        Args:
            content: Content to check
            
        Returns:
            List of blocked words found in the content
        """
        blocked_words = await self._get_blocked_words()
        content_lower = content.lower()
        
        found_words: list[str] = []
        
        for blocked in blocked_words:
            if not blocked.is_active:
                continue
            
            word = blocked.word.lower()
            
            # Use word boundary matching
            # \b matches word boundaries (spaces, punctuation, start/end)
            pattern = rf"\b{re.escape(word)}\b"
            
            if re.search(pattern, content_lower, re.IGNORECASE):
                found_words.append(blocked.word)
        
        return found_words
    
    async def _get_blocked_words(self) -> Sequence[BlockedWord]:
        """
        Get blocked words from cache or database.
        
        Uses Redis cache with fallback to in-memory cache.
        
        Returns:
            Sequence of BlockedWord models
        """
        # Try Redis cache first
        if self.redis:
            try:
                cached = await self.redis.get(BLOCKED_WORDS_CACHE_KEY)
                if cached:
                    import json
                    words_data = json.loads(cached)
                    # Convert back to BlockedWord-like objects
                    return [
                        BlockedWord(
                            id=w["id"],
                            word=w["word"],
                            severity=w["severity"],
                            category=w.get("category"),
                            is_active=w["is_active"],
                        )
                        for w in words_data
                    ]
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Fall back to in-memory cache
        if self._blocked_words_cache is not None:
            return self._blocked_words_cache
        
        # Load from database
        result = await self.db.execute(
            select(BlockedWord).where(BlockedWord.is_active == True)
        )
        words = result.scalars().all()
        
        # Update caches
        self._blocked_words_cache = list(words)
        
        if self.redis:
            try:
                import json
                words_data = [
                    {
                        "id": w.id,
                        "word": w.word,
                        "severity": w.severity,
                        "category": w.category,
                        "is_active": w.is_active,
                    }
                    for w in words
                ]
                await self.redis.set(
                    BLOCKED_WORDS_CACHE_KEY,
                    json.dumps(words_data),
                    ex=BLOCKED_WORDS_CACHE_TTL,
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return words
    
    async def invalidate_blocked_words_cache(self) -> None:
        """Invalidate the blocked words cache."""
        self._blocked_words_cache = None
        if self.redis:
            try:
                await self.redis.delete(BLOCKED_WORDS_CACHE_KEY)
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")
    
    # =========================================================================
    # Spam Pattern Detection
    # =========================================================================
    
    def check_spam_patterns(self, content: str) -> SpamCheckResult:
        """
        Check content for spam patterns.
        
        Detects:
        - Repeated characters: "AAAAA" or "!!!!!!"
        - Excessive uppercase: >70% caps in content
        - URL flooding: >3 URLs in content
        - Mention flooding: >10 @mentions in content
        
        Args:
            content: Content to check
            
        Returns:
            SpamCheckResult with details
        """
        reasons: list[str] = []
        score = 0.0
        
        # Check repeated characters
        repeated_chars = self._check_repeated_chars(content)
        if repeated_chars:
            reasons.append(f"Repeated characters detected: {repeated_chars[:3]}")
            score += 0.3
        
        # Check excessive uppercase
        excessive_caps = self._check_excessive_caps(content)
        if excessive_caps:
            reasons.append("Excessive uppercase (>70%)")
            score += 0.25
        
        # Check URL flooding
        url_flooding = self._check_url_flooding(content)
        if url_flooding:
            reasons.append(f"Too many URLs (>{MAX_URLS_ALLOWED})")
            score += 0.25
        
        # Check mention flooding
        mention_flooding = self._check_mention_flooding(content)
        if mention_flooding:
            reasons.append(f"Too many mentions (>{MAX_MENTIONS_ALLOWED})")
            score += 0.2
        
        # Clamp score to [0, 1]
        score = min(1.0, score)
        
        return SpamCheckResult(
            is_spam=score >= SPAM_SCORE_REVIEW_THRESHOLD,
            score=score,
            reasons=reasons,
            repeated_chars_detected=bool(repeated_chars),
            excessive_caps=excessive_caps,
            url_flooding=url_flooding,
            mention_flooding=mention_flooding,
        )
    
    def _check_repeated_chars(self, content: str) -> list[str]:
        """Find sequences of repeated characters."""
        matches = REPEATED_CHAR_PATTERN.findall(content)
        return matches
    
    def _check_excessive_caps(self, content: str) -> bool:
        """Check if content has too many uppercase letters."""
        # Only check content long enough to be meaningful
        if len(content) < MIN_CONTENT_LENGTH_FOR_CAPS_CHECK:
            return False
        
        # Filter to only letters
        letters = [c for c in content if c.isalpha()]
        if not letters:
            return False
        
        uppercase_count = sum(1 for c in letters if c.isupper())
        uppercase_ratio = uppercase_count / len(letters)
        
        return uppercase_ratio > UPPERCASE_PERCENTAGE_THRESHOLD
    
    def _check_url_flooding(self, content: str) -> bool:
        """Check if content has too many URLs."""
        urls = URL_PATTERN.findall(content)
        return len(urls) > MAX_URLS_ALLOWED
    
    def _check_mention_flooding(self, content: str) -> bool:
        """Check if content has too many @mentions."""
        mentions = MENTION_PATTERN.findall(content)
        return len(mentions) > MAX_MENTIONS_ALLOWED
    
    # =========================================================================
    # Toxicity Check (External API)
    # =========================================================================
    
    async def check_toxicity(self, content: str) -> float:
        """
        Check content toxicity using external API.
        
        This is an optional integration with services like:
        - Perspective API (Google)
        - OpenAI Moderation API
        - Custom toxicity model
        
        Args:
            content: Content to check
            
        Returns:
            Toxicity score from 0.0 to 1.0
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        if not self.toxicity_api_url:
            return 0.0
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {}
            if self.toxicity_api_key:
                headers["Authorization"] = f"Bearer {self.toxicity_api_key}"
            
            response = await client.post(
                self.toxicity_api_url,
                json={"content": content},
                headers=headers,
            )
            response.raise_for_status()
            
            data = response.json()
            # Expect response like {"toxicity": 0.5}
            return float(data.get("toxicity", 0.0))
    
    # =========================================================================
    # Action Determination
    # =========================================================================
    
    def _determine_action(
        self,
        flagged_words: list[str],
        spam_result: SpamCheckResult,
        toxicity_score: Optional[float],
    ) -> tuple[ModerationAction, Optional[str]]:
        """
        Determine the moderation action based on check results.
        
        Decision logic:
        1. High severity blocked words -> REJECT
        2. High spam score or toxicity -> REJECT
        3. Medium blocked words or scores -> REVIEW
        4. Otherwise -> APPROVE
        
        Args:
            flagged_words: Blocked words found
            spam_result: Spam check result
            toxicity_score: Optional toxicity score
            
        Returns:
            Tuple of (action, reason)
        """
        reasons: list[str] = []
        
        # Check for immediate rejection
        if flagged_words:
            reasons.append(f"Blocked words: {', '.join(flagged_words)}")
            # For now, any blocked word triggers review; severity could affect this
            return ModerationAction.REJECT, f"Content contains blocked words: {', '.join(flagged_words)}"
        
        if spam_result.score >= SPAM_SCORE_REJECT_THRESHOLD:
            return ModerationAction.REJECT, f"High spam score: {spam_result.score:.2f}"
        
        if toxicity_score is not None and toxicity_score >= TOXICITY_REJECT_THRESHOLD:
            return ModerationAction.REJECT, f"High toxicity score: {toxicity_score:.2f}"
        
        # Check for review
        if spam_result.score >= SPAM_SCORE_REVIEW_THRESHOLD:
            return ModerationAction.REVIEW, f"Moderate spam score: {spam_result.score:.2f}"
        
        if toxicity_score is not None and toxicity_score >= TOXICITY_REVIEW_THRESHOLD:
            return ModerationAction.REVIEW, f"Moderate toxicity score: {toxicity_score:.2f}"
        
        # Approve
        return ModerationAction.APPROVE, None
    
    # =========================================================================
    # Blocked Words Management
    # =========================================================================
    
    async def add_blocked_word(
        self,
        word: str,
        severity: str = "medium",
        category: Optional[str] = None,
    ) -> BlockedWord:
        """
        Add a new blocked word to the database.
        
        Args:
            word: The word to block
            severity: Severity level (low, medium, high)
            category: Optional category
            
        Returns:
            The created BlockedWord
        """
        blocked_word = BlockedWord(
            word=word.lower().strip(),
            severity=severity,
            category=category,
            is_active=True,
        )
        
        self.db.add(blocked_word)
        await self.db.flush()
        await self.db.refresh(blocked_word)
        
        # Invalidate cache
        await self.invalidate_blocked_words_cache()
        
        return blocked_word
    
    async def remove_blocked_word(self, word_id: int) -> bool:
        """
        Remove a blocked word (soft delete by setting inactive).
        
        Args:
            word_id: ID of the word to remove
            
        Returns:
            True if word was found and deactivated
        """
        result = await self.db.execute(
            select(BlockedWord).where(BlockedWord.id == word_id)
        )
        blocked_word = result.scalar_one_or_none()
        
        if not blocked_word:
            return False
        
        blocked_word.is_active = False
        await self.db.flush()
        
        # Invalidate cache
        await self.invalidate_blocked_words_cache()
        
        return True
    
    async def get_all_blocked_words(
        self, include_inactive: bool = False
    ) -> Sequence[BlockedWord]:
        """
        Get all blocked words.
        
        Args:
            include_inactive: Whether to include inactive words
            
        Returns:
            Sequence of BlockedWord models
        """
        query = select(BlockedWord)
        if not include_inactive:
            query = query.where(BlockedWord.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()


# =============================================================================
# Factory Function
# =============================================================================


def get_moderation_service(
    db: AsyncSession,
    redis: Optional[Redis] = None,
) -> ModerationService:
    """
    Factory function to create a ModerationService.
    
    Args:
        db: Async database session
        redis: Optional Redis client
        
    Returns:
        Configured ModerationService instance
    """
    return ModerationService(db, redis)

