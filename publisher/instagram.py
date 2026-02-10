"""Instagram publishing via Container API."""

import logging
import time
from typing import Optional

from config import get_settings
from publisher.meta_client import MetaAPIError, MetaClient

logger = logging.getLogger(__name__)


class InstagramPublisher:
    """Publish photos to Instagram using the Container API."""

    def __init__(self, client: Optional[MetaClient] = None):
        self.client = client or MetaClient()
        settings = get_settings()
        self.account_id = settings.instagram_business_account_id
        self.base_url = settings.base_url

    def _get_photo_url(self, storage_path: str) -> str:
        """Get the public URL for a photo."""
        return f"{self.base_url}/uploads/{storage_path}"

    def _create_media_container(
        self,
        image_url: str,
        caption: Optional[str] = None,
        is_carousel_item: bool = False,
    ) -> str:
        """Create a media container for a single image.

        Returns the container ID.
        """
        params = {
            "image_url": image_url,
        }

        if is_carousel_item:
            params["is_carousel_item"] = "true"
        elif caption:
            params["caption"] = caption

        result = self.client.post(f"{self.account_id}/media", params=params)
        container_id = result.get("id")

        if not container_id:
            raise MetaAPIError("No container ID returned")

        logger.info(f"Created media container: {container_id}")
        return container_id

    def _create_carousel_container(
        self,
        children_ids: list[str],
        caption: str,
    ) -> str:
        """Create a carousel container from child containers.

        Returns the carousel container ID.
        """
        params = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
        }

        result = self.client.post(f"{self.account_id}/media", params=params)
        container_id = result.get("id")

        if not container_id:
            raise MetaAPIError("No carousel container ID returned")

        logger.info(f"Created carousel container: {container_id}")
        return container_id

    def _wait_for_container(
        self,
        container_id: str,
        max_wait: int = 60,
        poll_interval: int = 5,
    ) -> bool:
        """Wait for a media container to finish processing.

        Returns True if container is ready, False if timed out.
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            result = self.client.get(
                container_id,
                params={"fields": "status_code,status"},
            )

            status = result.get("status_code")
            logger.debug(f"Container {container_id} status: {status}")

            if status == "FINISHED":
                return True
            elif status == "ERROR":
                error_msg = result.get("status", "Unknown error")
                raise MetaAPIError(f"Container processing failed: {error_msg}")

            time.sleep(poll_interval)

        return False

    def _publish_container(self, container_id: str) -> str:
        """Publish a media container.

        Returns the published media ID.
        """
        result = self.client.post(
            f"{self.account_id}/media_publish",
            params={"creation_id": container_id},
        )

        media_id = result.get("id")
        if not media_id:
            raise MetaAPIError("No media ID returned from publish")

        logger.info(f"Published media: {media_id}")
        return media_id

    def publish_single_photo(
        self,
        image_url: str,
        caption: str,
    ) -> str:
        """Publish a single photo to Instagram.

        Returns the published media ID.
        """
        # Create container
        container_id = self._create_media_container(image_url, caption=caption)

        # Wait for processing
        if not self._wait_for_container(container_id):
            raise MetaAPIError("Container processing timed out")

        # Publish
        return self._publish_container(container_id)

    def publish_carousel(
        self,
        image_urls: list[str],
        caption: str,
    ) -> str:
        """Publish a carousel (multiple photos) to Instagram.

        Returns the published media ID.
        """
        if len(image_urls) < 2:
            raise ValueError("Carousel requires at least 2 images")
        if len(image_urls) > 10:
            raise ValueError("Carousel supports maximum 10 images")

        # Create child containers for each image
        children_ids = []
        for url in image_urls:
            container_id = self._create_media_container(url, is_carousel_item=True)
            if not self._wait_for_container(container_id):
                raise MetaAPIError(f"Child container {container_id} processing timed out")
            children_ids.append(container_id)

        # Create carousel container
        carousel_id = self._create_carousel_container(children_ids, caption)

        # Wait for carousel processing
        if not self._wait_for_container(carousel_id):
            raise MetaAPIError("Carousel container processing timed out")

        # Publish
        return self._publish_container(carousel_id)

    def publish_post(
        self,
        photo_paths: list[str],
        caption: str,
        hashtags: Optional[list[str]] = None,
    ) -> str:
        """Publish a post to Instagram.

        Automatically chooses single photo or carousel based on number of images.
        Hashtags are appended to the caption.

        Returns the published media ID.
        """
        if not photo_paths:
            raise ValueError("At least one photo is required")

        # Build full caption with hashtags
        full_caption = caption
        if hashtags:
            hashtag_str = " ".join(hashtags)
            full_caption = f"{caption}\n\n{hashtag_str}"

        # Get public URLs for photos
        image_urls = [self._get_photo_url(path) for path in photo_paths]

        # Publish
        if len(image_urls) == 1:
            return self.publish_single_photo(image_urls[0], full_caption)
        else:
            return self.publish_carousel(image_urls, full_caption)
