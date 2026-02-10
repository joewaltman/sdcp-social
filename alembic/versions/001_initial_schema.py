"""Initial schema - posts, photos, approval_tokens tables.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Posts table
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_email", sa.String(255), nullable=False),
        sa.Column("source_message_id", sa.String(255), nullable=True),
        sa.Column("project_location", sa.String(255), nullable=True),
        sa.Column("project_type", sa.String(100), nullable=True),
        sa.Column("additional_context", sa.Text(), nullable=True),
        sa.Column("instagram_caption", sa.Text(), nullable=True),
        sa.Column("facebook_caption", sa.Text(), nullable=True),
        sa.Column("hashtags", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "pending_approval",
                "approved",
                "scheduled",
                "published",
                "rejected",
                "failed",
                name="poststatus",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("instagram_post_id", sa.String(255), nullable=True),
        sa.Column("facebook_post_id", sa.String(255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_message_id"),
    )
    op.create_index("ix_posts_status", "posts", ["status"])
    op.create_index("ix_posts_created_at", "posts", ["created_at"])

    # Photos table
    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("ai_description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_photos_post_id", "photos", ["post_id"])

    # Approval tokens table
    op.create_table(
        "approval_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "action",
            sa.Enum("approve", "reject", "edit", name="approvalaction"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_approval_tokens_token_hash", "approval_tokens", ["token_hash"])
    op.create_index("ix_approval_tokens_post_id", "approval_tokens", ["post_id"])


def downgrade() -> None:
    op.drop_table("approval_tokens")
    op.drop_table("photos")
    op.drop_table("posts")
    op.execute("DROP TYPE IF EXISTS approvalaction")
    op.execute("DROP TYPE IF EXISTS poststatus")
