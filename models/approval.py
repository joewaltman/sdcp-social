"""Approval token model for secure action links."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.post import Post


class ApprovalAction(enum.Enum):
    """Actions that can be performed via approval tokens."""

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"


class ApprovalToken(Base):
    """Secure token for approval/rejection/edit actions."""

    __tablename__ = "approval_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    # Token (stored as SHA256 hash)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # Action this token authorizes
    action: Mapped[ApprovalAction] = mapped_column(Enum(ApprovalAction), nullable=False)

    # Token lifecycle
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    post: Mapped["Post"] = relationship("Post", back_populates="approval_tokens")

    def __repr__(self) -> str:
        return f"<ApprovalToken(id={self.id}, action={self.action.value}, used={self.used_at is not None})>"

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        from datetime import timezone

        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_used(self) -> bool:
        """Check if the token has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid (not expired and not used)."""
        return not self.is_expired and not self.is_used
