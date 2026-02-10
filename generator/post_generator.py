"""Claude AI-powered social media post generator."""

import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import anthropic

from config import get_settings
from generator.prompts import (
    PHOTO_ANALYSIS_PROMPT,
    get_facebook_prompt,
    get_hashtag_prompt,
    get_instagram_prompt,
    get_system_prompt,
)

logger = logging.getLogger(__name__)


@dataclass
class GeneratedPost:
    """Container for generated post content."""

    instagram_caption: str
    facebook_caption: str
    hashtags: list[str]
    photo_descriptions: list[str]


class PostGenerator:
    """Generate social media posts using Claude's vision capabilities."""

    def __init__(self):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.system_prompt = get_system_prompt()

    def _encode_image(self, image_path: Path) -> tuple[str, str]:
        """Encode an image file to base64 and detect media type."""
        suffix = image_path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/jpeg")

        with open(image_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")

        return data, media_type

    def _build_image_content(
        self, image_paths: list[Path]
    ) -> list[dict]:
        """Build image content blocks for the API."""
        content = []
        for path in image_paths:
            data, media_type = self._encode_image(path)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": data,
                },
            })
        return content

    def _build_image_content_from_base64(
        self, images: list[tuple[str, str]]
    ) -> list[dict]:
        """Build image content blocks from base64-encoded images.

        Args:
            images: List of (base64_data, content_type) tuples
        """
        content = []
        for data, content_type in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": content_type,
                    "data": data,
                },
            })
        return content

    def analyze_photos(
        self,
        image_paths: Optional[list[Path]] = None,
        image_data: Optional[list[tuple[str, str]]] = None,
    ) -> list[str]:
        """Analyze photos and return descriptions.

        Args:
            image_paths: List of paths to image files
            image_data: List of (base64_data, content_type) tuples
        """
        if image_paths:
            image_content = self._build_image_content(image_paths)
        elif image_data:
            image_content = self._build_image_content_from_base64(image_data)
        else:
            return []

        descriptions = []
        for i, img_block in enumerate(image_content):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                img_block,
                                {"type": "text", "text": PHOTO_ANALYSIS_PROMPT},
                            ],
                        }
                    ],
                )
                descriptions.append(response.content[0].text)
            except Exception as e:
                logger.error(f"Error analyzing photo {i}: {e}")
                descriptions.append(f"Photo {i + 1}")

        return descriptions

    def generate_instagram_caption(
        self,
        context: str,
        image_paths: Optional[list[Path]] = None,
        image_data: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Generate an Instagram caption."""
        content = []

        if image_paths:
            content.extend(self._build_image_content(image_paths))
        elif image_data:
            content.extend(self._build_image_content_from_base64(image_data))

        content.append({"type": "text", "text": get_instagram_prompt(context)})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=self.system_prompt,
            messages=[{"role": "user", "content": content}],
        )

        return response.content[0].text.strip()

    def generate_facebook_caption(
        self,
        context: str,
        image_paths: Optional[list[Path]] = None,
        image_data: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Generate a Facebook caption."""
        content = []

        if image_paths:
            content.extend(self._build_image_content(image_paths))
        elif image_data:
            content.extend(self._build_image_content_from_base64(image_data))

        content.append({"type": "text", "text": get_facebook_prompt(context)})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            system=self.system_prompt,
            messages=[{"role": "user", "content": content}],
        )

        return response.content[0].text.strip()

    def generate_hashtags(self, context: str) -> list[str]:
        """Generate hashtags for the post."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": get_hashtag_prompt(context)}
            ],
        )

        text = response.content[0].text.strip()

        # Parse JSON array from response
        try:
            # Find JSON array in response
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                hashtags = json.loads(text[start:end])
                # Ensure all hashtags start with #
                return [h if h.startswith("#") else f"#{h}" for h in hashtags]
        except json.JSONDecodeError:
            logger.error(f"Failed to parse hashtags JSON: {text}")

        # Fallback: extract hashtags from text
        return [word for word in text.split() if word.startswith("#")]

    def generate_post(
        self,
        project_location: Optional[str] = None,
        project_type: Optional[str] = None,
        additional_context: Optional[str] = None,
        image_paths: Optional[list[Path]] = None,
        image_data: Optional[list[tuple[str, str]]] = None,
    ) -> GeneratedPost:
        """Generate a complete social media post with both captions and hashtags.

        Args:
            project_location: Location of the project (e.g., "La Jolla")
            project_type: Type of work (e.g., "interior painting", "cabinet refinishing")
            additional_context: Any additional context from the email
            image_paths: List of paths to image files
            image_data: List of (base64_data, content_type) tuples
        """
        # Build context string
        context_parts = []
        if project_location:
            context_parts.append(f"Location: {project_location}")
        if project_type:
            context_parts.append(f"Project type: {project_type}")
        if additional_context:
            context_parts.append(f"Additional details: {additional_context}")

        # Analyze photos first
        photo_descriptions = self.analyze_photos(image_paths, image_data)
        if photo_descriptions:
            context_parts.append(
                "Photo descriptions:\n" + "\n".join(f"- {d}" for d in photo_descriptions)
            )

        context = "\n".join(context_parts) if context_parts else "A painting project showcase"

        # Generate all content
        instagram_caption = self.generate_instagram_caption(context, image_paths, image_data)
        facebook_caption = self.generate_facebook_caption(context, image_paths, image_data)
        hashtags = self.generate_hashtags(context)

        return GeneratedPost(
            instagram_caption=instagram_caption,
            facebook_caption=facebook_caption,
            hashtags=hashtags,
            photo_descriptions=photo_descriptions,
        )
