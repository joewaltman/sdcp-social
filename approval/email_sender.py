"""Send approval emails via Postmark."""

import logging
from typing import Optional

from postmarker.core import PostmarkClient
from sqlalchemy.orm import Session

from approval.tokens import TokenManager
from config import get_settings
from models import Post

logger = logging.getLogger(__name__)


def _build_approval_email_html(
    post: Post,
    tokens: dict[str, str],
    token_manager: TokenManager,
) -> str:
    """Build the HTML content for the approval email."""
    settings = get_settings()

    # Build photo display
    photos_html = ""
    for photo in post.photos[:4]:  # Show max 4 photos
        photo_url = f"{settings.base_url}/uploads/{photo.storage_path}"
        photos_html += f'''
        <div style="margin: 10px; display: inline-block;">
            <img src="{photo_url}" style="max-width: 300px; max-height: 300px; border-radius: 8px;" />
        </div>
        '''

    # Build action URLs
    approve_url = token_manager.get_action_url("approve", tokens["approve"])
    edit_url = token_manager.get_action_url("edit", tokens["edit"])
    reject_url = token_manager.get_action_url("reject", tokens["reject"])

    # Format hashtags
    hashtags_str = " ".join(post.hashtags) if post.hashtags else ""

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #1e396d;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 20px;
                border: 1px solid #ddd;
                border-top: none;
                border-radius: 0 0 8px 8px;
            }}
            .photos {{
                text-align: center;
                margin: 20px 0;
                background: white;
                padding: 15px;
                border-radius: 8px;
            }}
            .caption-section {{
                background: white;
                padding: 15px;
                margin: 15px 0;
                border-radius: 8px;
                border-left: 4px solid #1e396d;
            }}
            .caption-title {{
                font-weight: bold;
                color: #1e396d;
                margin-bottom: 10px;
            }}
            .hashtags {{
                color: #666;
                font-size: 12px;
                margin-top: 10px;
            }}
            .actions {{
                text-align: center;
                margin: 30px 0;
            }}
            .btn {{
                display: inline-block;
                padding: 12px 24px;
                margin: 5px;
                border-radius: 6px;
                text-decoration: none;
                font-weight: bold;
                font-size: 14px;
            }}
            .btn-approve {{
                background-color: #28a745;
                color: white;
            }}
            .btn-edit {{
                background-color: #1e396d;
                color: white;
            }}
            .btn-reject {{
                background-color: #dc3545;
                color: white;
            }}
            .meta {{
                font-size: 12px;
                color: #666;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>New Post Ready for Review</h1>
        </div>
        <div class="content">
            <div class="photos">
                {photos_html}
            </div>

            <div class="caption-section">
                <div class="caption-title">Instagram Caption</div>
                <p>{post.instagram_caption or 'No caption generated'}</p>
            </div>

            <div class="caption-section">
                <div class="caption-title">Facebook Caption</div>
                <p>{post.facebook_caption or 'No caption generated'}</p>
            </div>

            <div class="caption-section">
                <div class="caption-title">Hashtags</div>
                <p class="hashtags">{hashtags_str}</p>
            </div>

            <div class="actions">
                <a href="{approve_url}" class="btn btn-approve">Approve & Schedule</a>
                <a href="{edit_url}" class="btn btn-edit">Edit Post</a>
                <a href="{reject_url}" class="btn btn-reject">Reject</a>
            </div>

            <div class="meta">
                <p><strong>Project:</strong> {post.project_type or 'Not specified'} in {post.project_location or 'San Diego'}</p>
                <p><strong>From:</strong> {post.source_email}</p>
                <p><strong>Photos:</strong> {post.photo_count}</p>
                <p>This link expires in {settings.approval_token_expiry_hours} hours.</p>
            </div>
        </div>
    </body>
    </html>
    '''

    return html


def _build_approval_email_text(
    post: Post,
    tokens: dict[str, str],
    token_manager: TokenManager,
) -> str:
    """Build plain text version of approval email."""
    settings = get_settings()

    approve_url = token_manager.get_action_url("approve", tokens["approve"])
    edit_url = token_manager.get_action_url("edit", tokens["edit"])
    reject_url = token_manager.get_action_url("reject", tokens["reject"])

    hashtags_str = " ".join(post.hashtags) if post.hashtags else ""

    text = f'''
NEW POST READY FOR REVIEW

Project: {post.project_type or 'Not specified'} in {post.project_location or 'San Diego'}
From: {post.source_email}
Photos: {post.photo_count}

---

INSTAGRAM CAPTION:
{post.instagram_caption or 'No caption generated'}

---

FACEBOOK CAPTION:
{post.facebook_caption or 'No caption generated'}

---

HASHTAGS:
{hashtags_str}

---

ACTIONS:

Approve & Schedule: {approve_url}

Edit Post: {edit_url}

Reject: {reject_url}

---

This link expires in {settings.approval_token_expiry_hours} hours.
'''

    return text


async def send_approval_email(
    post_id: int,
    db: Session,
) -> bool:
    """Send an approval email for a post.

    Returns True if email was sent successfully.
    """
    settings = get_settings()

    if not settings.postmark_server_token:
        logger.warning("Postmark token not configured, skipping approval email")
        return False

    # Get the post
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        logger.error(f"Post {post_id} not found")
        return False

    # Generate tokens
    token_manager = TokenManager(db)
    tokens = token_manager.generate_all_tokens(post_id)

    # Build email content
    html_body = _build_approval_email_html(post, tokens, token_manager)
    text_body = _build_approval_email_text(post, tokens, token_manager)

    # Send via Postmark
    try:
        client = PostmarkClient(server_token=settings.postmark_server_token)

        location_str = post.project_location or "San Diego"
        subject = f"New Post Ready: {post.project_type or 'Painting Project'} in {location_str}"

        for recipient in settings.approval_recipients_list:
            client.emails.send(
                From="noreply@sdcustompainting.com",
                To=recipient,
                Subject=subject,
                HtmlBody=html_body,
                TextBody=text_body,
                Tag="approval",
                TrackOpens=True,
            )
            logger.info(f"Sent approval email to {recipient} for post {post_id}")

        return True

    except Exception as e:
        logger.error(f"Failed to send approval email: {e}")
        return False
