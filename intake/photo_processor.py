"""Process and store photos from email attachments."""

import base64
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image

from config import get_settings
from schemas.postmark import PostmarkAttachment

logger = logging.getLogger(__name__)


@dataclass
class ProcessedPhoto:
    """Processed photo data ready for storage."""

    filename: str
    storage_path: str
    content_type: str
    file_size: int
    width: Optional[int]
    height: Optional[int]
    base64_data: str  # Keep for AI processing


class PhotoProcessor:
    """Process and store photos from email attachments."""

    # Supported image types
    SUPPORTED_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }

    # Size limits
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
    MIN_FILE_SIZE = 10 * 1024  # 10 KB (skip tiny images like email signatures)
    MIN_DIMENSION = 200  # Minimum width/height in pixels

    def __init__(self):
        settings = get_settings()
        self.storage_path = settings.photo_storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def process_attachments(
        self, attachments: list[PostmarkAttachment]
    ) -> list[ProcessedPhoto]:
        """Process a list of email attachments and return valid photos."""
        photos = []

        for attachment in attachments:
            try:
                photo = self.process_attachment(attachment)
                if photo:
                    photos.append(photo)
            except Exception as e:
                logger.error(f"Error processing attachment {attachment.Name}: {e}")

        return photos

    def process_attachment(
        self, attachment: PostmarkAttachment
    ) -> Optional[ProcessedPhoto]:
        """Process a single attachment and return photo data if valid."""
        # Check content type
        content_type = attachment.ContentType.lower()
        if content_type not in self.SUPPORTED_TYPES:
            logger.debug(f"Skipping unsupported type: {content_type}")
            return None

        # Check file size
        if attachment.ContentLength > self.MAX_FILE_SIZE:
            logger.warning(f"Attachment too large: {attachment.ContentLength} bytes")
            return None

        if attachment.ContentLength < self.MIN_FILE_SIZE:
            logger.debug(f"Attachment too small (likely signature): {attachment.ContentLength}")
            return None

        # Decode base64 content
        try:
            image_data = base64.b64decode(attachment.Content)
        except Exception as e:
            logger.error(f"Failed to decode base64: {e}")
            return None

        # Validate and get dimensions using PIL
        try:
            from io import BytesIO

            img = Image.open(BytesIO(image_data))
            width, height = img.size

            # Check minimum dimensions
            if width < self.MIN_DIMENSION or height < self.MIN_DIMENSION:
                logger.debug(f"Image too small: {width}x{height}")
                return None

        except Exception as e:
            logger.error(f"Failed to read image: {e}")
            return None

        # Generate unique filename and path
        file_ext = self.SUPPORTED_TYPES[content_type]
        unique_id = uuid.uuid4().hex[:12]
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        filename = f"{unique_id}{file_ext}"
        storage_subpath = f"{date_prefix}/{filename}"

        # Create directory structure
        full_dir = self.storage_path / date_prefix
        full_dir.mkdir(parents=True, exist_ok=True)

        # Save the file
        full_path = self.storage_path / storage_subpath
        with open(full_path, "wb") as f:
            f.write(image_data)

        logger.info(f"Saved photo: {storage_subpath} ({width}x{height})")

        return ProcessedPhoto(
            filename=attachment.Name or filename,
            storage_path=storage_subpath,
            content_type=content_type,
            file_size=len(image_data),
            width=width,
            height=height,
            base64_data=attachment.Content,
        )

    def get_full_path(self, storage_path: str) -> Path:
        """Get the full filesystem path for a stored photo."""
        return self.storage_path / storage_path

    def delete_photo(self, storage_path: str) -> bool:
        """Delete a stored photo."""
        try:
            full_path = self.get_full_path(storage_path)
            if full_path.exists():
                full_path.unlink()
                return True
        except Exception as e:
            logger.error(f"Error deleting photo {storage_path}: {e}")
        return False
