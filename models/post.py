"""Post model for social media posts."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.approval import ApprovalToken
    from models.photo import Photo


class PostStatus(enum.Enum):
    """Status workflow for posts."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    REJECTED = "rejected"
    FAILED = "failed"


class Post(Base):
    """Social media post model."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Source tracking (for deduplication)
    source_email: Mapped[str] = mapped_column(String(255), nullable=False)
    source_message_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)

    # Project context from email
    project_location: Mapped[Optional[str]] = mapped_column(String(255))
    project_type: Mapped[Optional[str]] = mapped_column(String(100))
    additional_context: Mapped[Optional[str]] = mapped_column(Text)

    # Generated content
    instagram_caption: Mapped[Optional[str]] = mapped_column(Text)
    facebook_caption: Mapped[Optional[str]] = mapped_column(Text)
    hashtags: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Status workflow
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, values_callable=lambda x: [e.value for e in x]),
        default=PostStatus.DRAFT,
        nullable=False,
    )

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Published post IDs from Meta
    instagram_post_id: Mapped[Optional[str]] = mapped_column(String(255))
    facebook_post_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Error tracking
    last_error: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    photos: Mapped[list["Photo"]] = relationship(
        "Photo", back_populates="post", cascade="all, delete-orphan", order_by="Photo.display_order"
    )
    approval_tokens: Mapped[list["ApprovalToken"]] = relationship(
        "ApprovalToken", back_populates="post", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Post(id={self.id}, status={self.status.value}, location={self.project_location})>"

    @property
    def primary_photo(self) -> Optional["Photo"]:
        """Get the primary photo for this post."""
        for photo in self.photos:
            if photo.is_primary:
                return photo
        return self.photos[0] if self.photos else None

    @property
    def photo_count(self) -> int:
        """Get the number of photos."""
        return len(self.photos)
