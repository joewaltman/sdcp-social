"""Application settings using Pydantic BaseSettings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "SDCP Social Post Generator"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    base_url: str = "http://localhost:8000"

    # Database
    database_url: str = "postgresql://localhost/sdcp_social"

    # Anthropic / Claude
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # Postmark
    postmark_server_token: str = ""
    postmark_inbound_address: str = "posts@inbound.postmarkapp.com"

    # Meta / Facebook / Instagram
    meta_access_token: str = ""
    facebook_page_id: str = ""
    instagram_business_account_id: str = ""

    # Approval workflow
    approval_email_recipients: str = "emily@sdcustompainting.com"
    approval_token_expiry_hours: int = 72

    # Photo storage
    photo_storage_path: Path = Path("./uploads")

    # Timezone
    timezone: str = "America/Los_Angeles"

    # Default publish time (24-hour format)
    default_publish_hour: int = 10
    default_publish_minute: int = 0

    # Dashboard authentication
    dashboard_password: str = ""

    @property
    def approval_recipients_list(self) -> list[str]:
        """Parse comma-separated approval recipients."""
        return [email.strip() for email in self.approval_email_recipients.split(",")]

    @property
    def brand_voice_path(self) -> Path:
        """Path to brand voice markdown file."""
        return Path(__file__).parent / "brand_voice.md"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
