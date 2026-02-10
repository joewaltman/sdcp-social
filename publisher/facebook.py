"""Facebook publishing via Graph API."""

import logging
from typing import Optional

from config import get_settings
from publisher.meta_client import MetaAPIError, MetaClient

logger = logging.getLogger(__name__)


class FacebookPublisher:
    """Publish photos to Facebook Page."""

    def __init__(self, client: Optional[MetaClient] = None):
        self.client = client or MetaClient()
        settings = get_settings()
        self.page_id = settings.facebook_page_id
        self.base_url = settings.base_url

    def _get_photo_url(self, storage_path: str) -> str:
        """Get the public URL for a photo."""
        return f"{self.base_url}/uploads/{storage_path}"

    def publish_single_photo(
        self,
        image_url: str,
        message: str,
    ) -> str:
        """Publish a single photo to Facebook Page.

        Returns the post ID.
        """
        result = self.client.post(
            f"{self.page_id}/photos",
            params={
                "url": image_url,
                "message": message,
                "published": "true",
            },
        )

        post_id = result.get("post_id") or result.get("id")
        if not post_id:
            raise MetaAPIError("No post ID returned")

        logger.info(f"Published Facebook photo: {post_id}")
        return post_id

    def publish_multi_photo(
        self,
        image_urls: list[str],
        message: str,
    ) -> str:
        """Publish multiple photos as a single Facebook post.

        Returns the post ID.
        """
        if len(image_urls) < 2:
            raise ValueError("Multi-photo post requires at least 2 images")

        # First, upload each photo as unpublished
        photo_ids = []
        for url in image_urls:
            result = self.client.post(
                f"{self.page_id}/photos",
                params={
                    "url": url,
                    "published": "false",
                },
            )
            photo_id = result.get("id")
            if photo_id:
                photo_ids.append(photo_id)
                logger.debug(f"Uploaded unpublished photo: {photo_id}")

        if not photo_ids:
            raise MetaAPIError("No photos were uploaded")

        # Create a post with the attached photos
        attached_media = [{"media_fbid": pid} for pid in photo_ids]

        result = self.client.post(
            f"{self.page_id}/feed",
            params={
                "message": message,
                "attached_media": str(attached_media).replace("'", '"'),
            },
        )

        post_id = result.get("id")
        if not post_id:
            raise MetaAPIError("No post ID returned")

        logger.info(f"Published Facebook multi-photo post: {post_id}")
        return post_id

    def publish_post(
        self,
        photo_paths: list[str],
        message: str,
    ) -> str:
        """Publish a post to Facebook.

        Automatically chooses single photo or multi-photo based on number of images.

        Returns the post ID.
        """
        if not photo_paths:
            raise ValueError("At least one photo is required")

        # Get public URLs for photos
        image_urls = [self._get_photo_url(path) for path in photo_paths]

        # Publish
        if len(image_urls) == 1:
            return self.publish_single_photo(image_urls[0], message)
        else:
            return self.publish_multi_photo(image_urls, message)

    def publish_link(
        self,
        link: str,
        message: Optional[str] = None,
    ) -> str:
        """Publish a link post to Facebook.

        Returns the post ID.
        """
        params = {"link": link}
        if message:
            params["message"] = message

        result = self.client.post(f"{self.page_id}/feed", params=params)

        post_id = result.get("id")
        if not post_id:
            raise MetaAPIError("No post ID returned")

        logger.info(f"Published Facebook link post: {post_id}")
        return post_id
