"""Secure token generation and validation for approval workflow."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from config import get_settings
from models.approval import ApprovalAction, ApprovalToken


class TokenManager:
    """Manage secure approval tokens."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _hash_token(self, token: str) -> str:
        """Create a SHA256 hash of the token."""
        return hashlib.sha256(token.encode()).hexdigest()

    def generate_token(
        self,
        post_id: int,
        action: ApprovalAction,
        expiry_hours: Optional[int] = None,
    ) -> str:
        """Generate a new approval token for a post.

        Returns the raw token (not the hash) for use in URLs.
        """
        # Generate secure random token
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)

        # Calculate expiry
        if expiry_hours is None:
            expiry_hours = self.settings.approval_token_expiry_hours
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

        # Create token record
        token = ApprovalToken(
            post_id=post_id,
            token_hash=token_hash,
            action=action,
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.commit()

        return raw_token

    def generate_all_tokens(self, post_id: int) -> dict[str, str]:
        """Generate approve, reject, and edit tokens for a post.

        Returns dict mapping action name to raw token.
        """
        # Invalidate any existing unused tokens for this post
        self.invalidate_tokens(post_id)

        return {
            "approve": self.generate_token(post_id, ApprovalAction.APPROVE),
            "reject": self.generate_token(post_id, ApprovalAction.REJECT),
            "edit": self.generate_token(post_id, ApprovalAction.EDIT),
        }

    def validate_token(self, raw_token: str) -> Optional[ApprovalToken]:
        """Validate a token and return the ApprovalToken if valid.

        Returns None if token is invalid, expired, or already used.
        """
        token_hash = self._hash_token(raw_token)

        token = (
            self.db.query(ApprovalToken)
            .filter(ApprovalToken.token_hash == token_hash)
            .first()
        )

        if not token:
            return None

        if not token.is_valid:
            return None

        return token

    def use_token(self, raw_token: str) -> Optional[ApprovalToken]:
        """Mark a token as used and return it.

        Returns the token if valid and successfully marked as used,
        None otherwise.
        """
        token = self.validate_token(raw_token)
        if not token:
            return None

        token.used_at = datetime.now(timezone.utc)
        self.db.commit()

        return token

    def invalidate_tokens(self, post_id: int) -> int:
        """Invalidate all unused tokens for a post.

        Returns the number of tokens invalidated.
        """
        now = datetime.now(timezone.utc)
        result = (
            self.db.query(ApprovalToken)
            .filter(
                ApprovalToken.post_id == post_id,
                ApprovalToken.used_at.is_(None),
            )
            .update({"used_at": now})
        )
        self.db.commit()
        return result

    def get_action_url(self, action: str, token: str) -> str:
        """Generate the full URL for an approval action."""
        base_url = self.settings.base_url.rstrip("/")
        return f"{base_url}/approve/{action}/{token}"
