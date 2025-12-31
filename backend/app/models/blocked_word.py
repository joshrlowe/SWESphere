"""
BlockedWord model for content moderation.

Stores words and phrases that should be blocked or flagged in user content.
"""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import BaseModelMixin


class BlockedWord(Base, BaseModelMixin):
    """
    Model for storing blocked words for content moderation.
    
    Attributes:
        id: Primary key
        word: The blocked word or phrase
        severity: Severity level (low, medium, high)
        category: Category of the word (hate, spam, adult, etc.)
        is_active: Whether this rule is currently active
    """
    
    __tablename__ = "blocked_words"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Word content
    word: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="The blocked word or phrase",
    )
    
    # Severity: low, medium, high
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        doc="Severity level: low (flag), medium (review), high (reject)",
    )
    
    # Category for organization
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Category: hate, spam, adult, violence, etc.",
    )
    
    # Active flag for soft enable/disable
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this blocked word rule is active",
    )
    
    def __repr__(self) -> str:
        return f"<BlockedWord(id={self.id}, word={self.word!r}, severity={self.severity})>"

