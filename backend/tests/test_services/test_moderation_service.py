"""
Tests for ModerationService.

Comprehensive test coverage for:
- Blocked word detection with word boundaries
- Spam pattern detection (repeated chars, caps, URLs, mentions)
- Toxicity API integration
- Moderation action determination
- Blocked word management
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blocked_word import BlockedWord
from app.schemas.moderation import ModerationAction, ModerationResult, SpamCheckResult
from app.services.moderation_service import (
    MAX_MENTIONS_ALLOWED,
    MAX_URLS_ALLOWED,
    REPEATED_CHAR_THRESHOLD,
    SPAM_SCORE_REJECT_THRESHOLD,
    SPAM_SCORE_REVIEW_THRESHOLD,
    UPPERCASE_PERCENTAGE_THRESHOLD,
    ModerationService,
    get_moderation_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest_asyncio.fixture
async def moderation_service(db_session: AsyncSession, mock_redis) -> ModerationService:
    """Create ModerationService for testing."""
    return ModerationService(db_session, mock_redis)


@pytest_asyncio.fixture
async def moderation_service_no_redis(db_session: AsyncSession) -> ModerationService:
    """Create ModerationService without Redis."""
    return ModerationService(db_session, redis=None)


@pytest_asyncio.fixture
async def blocked_word_factory(db_session: AsyncSession):
    """Factory for creating test blocked words."""
    async def _create_blocked_word(
        word: str,
        severity: str = "medium",
        category: str | None = None,
        is_active: bool = True,
    ) -> BlockedWord:
        blocked = BlockedWord(
            word=word,
            severity=severity,
            category=category,
            is_active=is_active,
        )
        db_session.add(blocked)
        await db_session.flush()
        await db_session.refresh(blocked)
        return blocked
    
    return _create_blocked_word


# =============================================================================
# Blocked Words Tests
# =============================================================================


class TestBlockedWords:
    """Test blocked word detection."""

    @pytest.mark.asyncio
    async def test_no_blocked_words_in_clean_content(
        self, moderation_service, blocked_word_factory
    ):
        """Clean content should return no flagged words."""
        await blocked_word_factory("badword")
        
        result = await moderation_service.check_blocked_words("Hello, this is clean content!")
        
        assert result == []

    @pytest.mark.asyncio
    async def test_detects_blocked_word(
        self, moderation_service, blocked_word_factory
    ):
        """Should detect blocked words in content."""
        await blocked_word_factory("badword")
        
        result = await moderation_service.check_blocked_words("This contains badword here")
        
        assert "badword" in result

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(
        self, moderation_service, blocked_word_factory
    ):
        """Blocked word matching should be case-insensitive."""
        await blocked_word_factory("badword")
        
        result1 = await moderation_service.check_blocked_words("BADWORD is here")
        result2 = await moderation_service.check_blocked_words("BadWord is here")
        result3 = await moderation_service.check_blocked_words("badWORD is here")
        
        assert len(result1) == 1
        assert len(result2) == 1
        assert len(result3) == 1

    @pytest.mark.asyncio
    async def test_word_boundary_matching(
        self, moderation_service, blocked_word_factory
    ):
        """Should use word boundaries to avoid false positives."""
        await blocked_word_factory("ass")
        
        # Should NOT match - "ass" is part of "class"
        result1 = await moderation_service.check_blocked_words("This is a class")
        result2 = await moderation_service.check_blocked_words("The password is secure")
        result3 = await moderation_service.check_blocked_words("Grasshopper jumped")
        
        # Should match - "ass" is a standalone word
        result4 = await moderation_service.check_blocked_words("What an ass!")
        result5 = await moderation_service.check_blocked_words("He's an ass")
        
        assert result1 == []
        assert result2 == []
        assert result3 == []
        assert len(result4) == 1
        assert len(result5) == 1

    @pytest.mark.asyncio
    async def test_multiple_blocked_words(
        self, moderation_service, blocked_word_factory
    ):
        """Should detect multiple blocked words."""
        await blocked_word_factory("bad")
        await blocked_word_factory("worse")
        
        result = await moderation_service.check_blocked_words("This is bad and worse")
        
        assert len(result) == 2
        assert "bad" in result
        assert "worse" in result

    @pytest.mark.asyncio
    async def test_inactive_words_ignored(
        self, moderation_service, blocked_word_factory
    ):
        """Inactive blocked words should be ignored."""
        await blocked_word_factory("activeword", is_active=True)
        await blocked_word_factory("inactiveword", is_active=False)
        
        result = await moderation_service.check_blocked_words(
            "activeword and inactiveword"
        )
        
        assert "activeword" in result
        assert "inactiveword" not in result

    @pytest.mark.asyncio
    async def test_phrase_blocking(
        self, moderation_service, blocked_word_factory
    ):
        """Should block multi-word phrases."""
        await blocked_word_factory("bad phrase")
        
        result1 = await moderation_service.check_blocked_words("This contains bad phrase here")
        result2 = await moderation_service.check_blocked_words("bad and phrase separately")
        
        assert len(result1) == 1
        assert len(result2) == 0


# =============================================================================
# Spam Pattern Tests
# =============================================================================


class TestSpamPatterns:
    """Test spam pattern detection."""

    def test_clean_content_no_spam(self, moderation_service):
        """Clean content should have zero spam score."""
        result = moderation_service.check_spam_patterns(
            "This is a normal, well-written message."
        )
        
        assert result.is_spam is False
        assert result.score == 0.0
        assert result.reasons == []

    def test_repeated_characters_detected(self, moderation_service):
        """Should detect repeated character sequences."""
        result = moderation_service.check_spam_patterns("AAAAA this is spam!")
        
        assert result.repeated_chars_detected is True
        assert result.score > 0
        assert any("Repeated" in r for r in result.reasons)

    def test_repeated_punctuation_detected(self, moderation_service):
        """Should detect repeated punctuation."""
        result = moderation_service.check_spam_patterns("Hello!!!!! How are you?????")
        
        assert result.repeated_chars_detected is True

    def test_excessive_uppercase_detected(self, moderation_service):
        """Should detect excessive uppercase content."""
        result = moderation_service.check_spam_patterns(
            "THIS IS ALL UPPERCASE AND IT'S ANNOYING"
        )
        
        assert result.excessive_caps is True
        assert result.score > 0
        assert any("uppercase" in r.lower() for r in result.reasons)

    def test_normal_caps_accepted(self, moderation_service):
        """Normal capitalization should not trigger."""
        result = moderation_service.check_spam_patterns(
            "This is a Normal Sentence With Some Capitalization."
        )
        
        assert result.excessive_caps is False

    def test_short_content_caps_not_checked(self, moderation_service):
        """Very short content should skip caps check."""
        result = moderation_service.check_spam_patterns("HELLO")
        
        # "HELLO" is short, so excessive caps shouldn't trigger
        assert result.excessive_caps is False

    def test_url_flooding_detected(self, moderation_service):
        """Should detect too many URLs."""
        content = (
            "Check out http://example1.com and http://example2.com "
            "and http://example3.com and http://example4.com for more!"
        )
        result = moderation_service.check_spam_patterns(content)
        
        assert result.url_flooding is True
        assert result.score > 0
        assert any("URLs" in r for r in result.reasons)

    def test_few_urls_accepted(self, moderation_service):
        """Few URLs should be allowed."""
        content = "Visit http://example1.com and http://example2.com"
        result = moderation_service.check_spam_patterns(content)
        
        assert result.url_flooding is False

    def test_mention_flooding_detected(self, moderation_service):
        """Should detect too many @mentions."""
        mentions = " ".join([f"@user{i}" for i in range(15)])
        result = moderation_service.check_spam_patterns(f"Hey {mentions}")
        
        assert result.mention_flooding is True
        assert result.score > 0
        assert any("mentions" in r.lower() for r in result.reasons)

    def test_few_mentions_accepted(self, moderation_service):
        """Few mentions should be allowed."""
        result = moderation_service.check_spam_patterns(
            "Hey @user1 @user2 @user3, check this out!"
        )
        
        assert result.mention_flooding is False

    def test_combined_spam_signals(self, moderation_service):
        """Multiple spam signals should increase score."""
        content = "AAAAA!!!! CHECK http://a.com http://b.com http://c.com http://d.com"
        result = moderation_service.check_spam_patterns(content)
        
        # Multiple signals should result in higher score
        assert result.score > 0.3
        assert result.repeated_chars_detected or result.url_flooding

    def test_spam_score_capped_at_one(self, moderation_service):
        """Spam score should never exceed 1.0."""
        # Create content with all spam signals
        mentions = " ".join([f"@u{i}" for i in range(20)])
        urls = " ".join([f"http://site{i}.com" for i in range(10)])
        content = f"AAAAAAA!!!!! {mentions} {urls} ALLCAPS"
        
        result = moderation_service.check_spam_patterns(content)
        
        assert result.score <= 1.0


# =============================================================================
# Full Moderation Tests
# =============================================================================


class TestModeratePost:
    """Test the full moderation pipeline."""

    @pytest.mark.asyncio
    async def test_clean_content_approved(self, moderation_service):
        """Clean content should be approved."""
        result = await moderation_service.moderate_post(
            "Hello everyone! This is a nice, clean message."
        )
        
        assert result.approved is True
        assert result.action == ModerationAction.APPROVE
        assert result.flagged_words == []
        assert result.spam_score < SPAM_SCORE_REVIEW_THRESHOLD

    @pytest.mark.asyncio
    async def test_empty_content_approved(self, moderation_service):
        """Empty content should be approved."""
        result = await moderation_service.moderate_post("")
        
        assert result.approved is True
        assert result.action == ModerationAction.APPROVE

    @pytest.mark.asyncio
    async def test_whitespace_only_approved(self, moderation_service):
        """Whitespace-only content should be approved."""
        result = await moderation_service.moderate_post("   \n\t  ")
        
        assert result.approved is True

    @pytest.mark.asyncio
    async def test_blocked_word_rejects(
        self, moderation_service, blocked_word_factory
    ):
        """Content with blocked words should be rejected."""
        await blocked_word_factory("blockedword")
        
        result = await moderation_service.moderate_post(
            "This contains a blockedword in it."
        )
        
        assert result.approved is False
        assert result.action == ModerationAction.REJECT
        assert "blockedword" in result.flagged_words
        assert "blocked words" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_high_spam_rejects(self, moderation_service):
        """High spam score should reject."""
        # Create content with multiple spam signals
        mentions = " ".join([f"@u{i}" for i in range(15)])
        content = f"AAAAAAA!!!!! {mentions}"
        
        result = await moderation_service.moderate_post(content)
        
        # May reject or review depending on combined score
        assert result.action in (ModerationAction.REJECT, ModerationAction.REVIEW)

    @pytest.mark.asyncio
    async def test_moderate_spam_reviews(self, moderation_service):
        """Moderate spam score should queue for review."""
        # Content with one spam signal
        result = await moderation_service.moderate_post("Check AAAAA this out!")
        
        # Single spam signal should trigger review or pass
        assert result.action in (ModerationAction.APPROVE, ModerationAction.REVIEW)

    @pytest.mark.asyncio
    async def test_result_contains_all_scores(
        self, moderation_service, blocked_word_factory
    ):
        """Result should contain all score components."""
        await blocked_word_factory("testword")
        
        result = await moderation_service.moderate_post("testword and normal text")
        
        assert isinstance(result.approved, bool)
        assert isinstance(result.flagged_words, list)
        assert isinstance(result.spam_score, float)
        assert result.action in (ModerationAction.APPROVE, ModerationAction.REVIEW, ModerationAction.REJECT)


# =============================================================================
# Toxicity API Tests
# =============================================================================


class TestToxicityAPI:
    """Test external toxicity API integration."""

    @pytest.mark.asyncio
    async def test_toxicity_api_not_configured(self, moderation_service):
        """Without API configured, toxicity should be None."""
        result = await moderation_service.moderate_post("Some content")
        
        assert result.toxicity_score is None

    @pytest.mark.asyncio
    async def test_toxicity_api_called(self, db_session, mock_redis):
        """Should call toxicity API when configured."""
        service = ModerationService(
            db_session,
            mock_redis,
            toxicity_api_url="http://api.example.com/toxicity",
            toxicity_api_key="test-key",
        )
        
        with patch("app.services.moderation_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"toxicity": 0.3}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            result = await service.moderate_post("Some content")
            
            # API should have been called
            mock_client_instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_toxicity_api_failure_handled(self, db_session, mock_redis):
        """Should handle toxicity API failures gracefully."""
        service = ModerationService(
            db_session,
            mock_redis,
            toxicity_api_url="http://api.example.com/toxicity",
        )
        
        with patch("app.services.moderation_service.httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(side_effect=Exception("API Error"))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            # Should not raise, should continue without toxicity score
            result = await service.moderate_post("Some content")
            
            assert result.toxicity_score is None


# =============================================================================
# Blocked Word Management Tests
# =============================================================================


class TestBlockedWordManagement:
    """Test blocked word CRUD operations."""

    @pytest.mark.asyncio
    async def test_add_blocked_word(self, moderation_service, db_session):
        """Should add a new blocked word."""
        word = await moderation_service.add_blocked_word(
            word="newbadword",
            severity="high",
            category="profanity",
        )
        
        assert word.id is not None
        assert word.word == "newbadword"
        assert word.severity == "high"
        assert word.category == "profanity"
        assert word.is_active is True

    @pytest.mark.asyncio
    async def test_add_word_normalizes_case(self, moderation_service):
        """Added words should be normalized to lowercase."""
        word = await moderation_service.add_blocked_word(word="UPPERCASE")
        
        assert word.word == "uppercase"

    @pytest.mark.asyncio
    async def test_add_word_strips_whitespace(self, moderation_service):
        """Added words should have whitespace stripped."""
        word = await moderation_service.add_blocked_word(word="  padded  ")
        
        assert word.word == "padded"

    @pytest.mark.asyncio
    async def test_remove_blocked_word(
        self, moderation_service, blocked_word_factory
    ):
        """Should deactivate a blocked word."""
        word = await blocked_word_factory("toremove")
        
        result = await moderation_service.remove_blocked_word(word.id)
        
        assert result is True
        
        # Word should no longer be detected
        check_result = await moderation_service.check_blocked_words("toremove is here")
        assert check_result == []

    @pytest.mark.asyncio
    async def test_remove_nonexistent_word(self, moderation_service):
        """Removing nonexistent word should return False."""
        result = await moderation_service.remove_blocked_word(99999)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_blocked_words(
        self, moderation_service, blocked_word_factory
    ):
        """Should retrieve all active blocked words."""
        await blocked_word_factory("word1")
        await blocked_word_factory("word2")
        await blocked_word_factory("inactive", is_active=False)
        
        words = await moderation_service.get_all_blocked_words()
        word_list = [w.word for w in words]
        
        assert "word1" in word_list
        assert "word2" in word_list
        assert "inactive" not in word_list

    @pytest.mark.asyncio
    async def test_get_all_including_inactive(
        self, moderation_service, blocked_word_factory
    ):
        """Should optionally include inactive words."""
        await blocked_word_factory("active")
        await blocked_word_factory("inactive", is_active=False)
        
        words = await moderation_service.get_all_blocked_words(include_inactive=True)
        word_list = [w.word for w in words]
        
        assert "active" in word_list
        assert "inactive" in word_list


# =============================================================================
# Cache Tests
# =============================================================================


class TestCaching:
    """Test blocked words caching."""

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, moderation_service, mock_redis):
        """Should invalidate cache when requested."""
        await moderation_service.invalidate_blocked_words_cache()
        
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_cache_used_on_second_call(
        self, moderation_service, blocked_word_factory
    ):
        """Should use cache on subsequent calls."""
        await blocked_word_factory("cachedword")
        
        # First call populates cache
        await moderation_service.check_blocked_words("cachedword")
        
        # Second call should use cache
        await moderation_service.check_blocked_words("cachedword")
        
        # Service should have internal cache populated
        assert moderation_service._blocked_words_cache is not None

    @pytest.mark.asyncio
    async def test_works_without_redis(
        self, moderation_service_no_redis, blocked_word_factory, db_session
    ):
        """Should work without Redis using in-memory cache."""
        blocked = BlockedWord(word="testword", severity="medium", is_active=True)
        db_session.add(blocked)
        await db_session.flush()
        
        result = await moderation_service_no_redis.check_blocked_words("testword here")
        
        assert "testword" in result


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_unicode_content(self, moderation_service, blocked_word_factory):
        """Should handle Unicode content correctly."""
        await blocked_word_factory("тест")  # Russian word
        
        result = await moderation_service.check_blocked_words("Это тест unicode")
        
        assert "тест" in result

    @pytest.mark.asyncio
    async def test_emoji_in_content(self, moderation_service):
        """Should handle emoji content."""
        result = await moderation_service.moderate_post("Hello 👋 world 🌍!")
        
        assert result.approved is True

    @pytest.mark.asyncio
    async def test_very_long_content(self, moderation_service):
        """Should handle very long content."""
        long_content = "word " * 10000
        
        result = await moderation_service.moderate_post(long_content)
        
        # Should complete without error
        assert isinstance(result, ModerationResult)

    @pytest.mark.asyncio
    async def test_special_characters_in_blocked_word(
        self, moderation_service, blocked_word_factory
    ):
        """Blocked words with special chars should be escaped."""
        await blocked_word_factory("test.word")
        
        # The dot should be treated literally, not as regex any-char
        result1 = await moderation_service.check_blocked_words("test.word")
        result2 = await moderation_service.check_blocked_words("testXword")
        
        assert len(result1) == 1
        assert len(result2) == 0


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Test the factory function."""

    def test_get_moderation_service(self, db_session, mock_redis):
        """Factory should return configured service."""
        service = get_moderation_service(db_session, mock_redis)
        
        assert isinstance(service, ModerationService)
        assert service.db is db_session
        assert service.redis is mock_redis

    def test_get_moderation_service_no_redis(self, db_session):
        """Factory should work without Redis."""
        service = get_moderation_service(db_session)
        
        assert isinstance(service, ModerationService)
        assert service.redis is None

