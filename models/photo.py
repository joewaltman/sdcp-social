"""Photo model for post images."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.post import Post


class Photo(Base):
    """Photo/image model for posts."""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Image dimensions
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)

    # AI analysis cache
    ai_description: Mapped[Optional[str]] = mapped_column(Text)

    # Display settings
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    post: Mapped["Post"] = relationship("Post", back_populates="photos")

    def __repr__(self) -> str:
        return f"<Photo(id={self.id}, filename={self.filename}, primary={self.is_primary})>"

    @property
    def url(self) -> str:
        """Get the URL for serving this photo."""
        from config import get_settings

        settings = get_settings()
        return f"{settings.base_url}/uploads/{self.storage_path}"
