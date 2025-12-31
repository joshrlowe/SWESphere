"""
Moderation schemas for content moderation system.

Defines the data structures for moderation results and requests.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ModerationAction(str, Enum):
    """Possible actions from moderation."""
    
    APPROVE = "approve"
    REVIEW = "review"
    REJECT = "reject"


class ModerationResult(BaseModel):
    """
    Result of content moderation check.
    
    Attributes:
        approved: Whether the content passed moderation
        flagged_words: List of blocked words found in content
        spam_score: Score from 0.0 to 1.0 indicating spam likelihood
        toxicity_score: Optional score from external API (0.0 to 1.0)
        action: Recommended action (approve, review, reject)
        reason: Human-readable explanation of the decision
    """
    
    approved: bool = Field(
        ...,
        description="Whether the content passed moderation",
    )
    flagged_words: list[str] = Field(
        default_factory=list,
        description="List of blocked words found in content",
    )
    spam_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Spam likelihood score (0.0 = not spam, 1.0 = definite spam)",
    )
    toxicity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Toxicity score from external API",
    )
    action: ModerationAction = Field(
        ...,
        description="Recommended moderation action",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of the decision",
    )

    class Config:
        use_enum_values = True


class BlockedWordCreate(BaseModel):
    """Schema for creating a new blocked word."""
    
    word: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The word or phrase to block",
    )
    severity: str = Field(
        default="medium",
        description="Severity level: low, medium, high",
    )
    category: Optional[str] = Field(
        default=None,
        description="Category of the blocked word (e.g., hate, spam, adult)",
    )


class BlockedWordResponse(BaseModel):
    """Schema for blocked word response."""
    
    id: int
    word: str
    severity: str
    category: Optional[str]
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class BlockedWordUpdate(BaseModel):
    """Schema for updating a blocked word."""
    
    word: Optional[str] = Field(None, min_length=1, max_length=100)
    severity: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class SpamCheckResult(BaseModel):
    """Detailed spam check result."""
    
    is_spam: bool
    score: float
    reasons: list[str] = Field(default_factory=list)
    repeated_chars_detected: bool = False
    excessive_caps: bool = False
    url_flooding: bool = False
    mention_flooding: bool = False

