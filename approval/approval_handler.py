"""Handle approval action requests."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from approval.tokens import TokenManager
from config import get_settings
from models import Post, PostStatus, get_db
from models.approval import ApprovalAction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/approve", tags=["approval"])


def _success_html(title: str, message: str, redirect_url: Optional[str] = None) -> str:
    """Generate success HTML response."""
    settings = get_settings()
    redirect_meta = ""
    if redirect_url:
        redirect_meta = f'<meta http-equiv="refresh" content="3;url={redirect_url}">'

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        {redirect_meta}
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background-color: #f5f5f5;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 500px;
            }}
            .icon {{
                font-size: 48px;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #1e396d;
                margin-bottom: 10px;
            }}
            p {{
                color: #666;
                line-height: 1.6;
            }}
            a {{
                color: #1e396d;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✓</div>
            <h1>{title}</h1>
            <p>{message}</p>
            <p><a href="{settings.base_url}">Go to Dashboard</a></p>
        </div>
    </body>
    </html>
    '''


def _error_html(title: str, message: str) -> str:
    """Generate error HTML response."""
    settings = get_settings()
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background-color: #f5f5f5;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 500px;
            }}
            .icon {{
                font-size: 48px;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #dc3545;
                margin-bottom: 10px;
            }}
            p {{
                color: #666;
                line-height: 1.6;
            }}
            a {{
                color: #1e396d;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✗</div>
            <h1>{title}</h1>
            <p>{message}</p>
            <p><a href="{settings.base_url}">Go to Dashboard</a></p>
        </div>
    </body>
    </html>
    '''


def handle_approval_action(
    token: str,
    action: str,
    db: Session,
) -> tuple[bool, str, Optional[Post]]:
    """Handle an approval action.

    Returns: (success, message, post)
    """
    token_manager = TokenManager(db)

    # Validate and use the token
    approval_token = token_manager.use_token(token)
    if not approval_token:
        return False, "Invalid or expired token", None

    # Verify action matches token
    expected_action = {
        "approve": ApprovalAction.APPROVE,
        "reject": ApprovalAction.REJECT,
        "edit": ApprovalAction.EDIT,
    }.get(action.lower())

    if not expected_action or approval_token.action != expected_action:
        return False, "Action mismatch", None

    # Get the post
    post = db.query(Post).filter(Post.id == approval_token.post_id).first()
    if not post:
        return False, "Post not found", None

    # Handle each action
    if expected_action == ApprovalAction.APPROVE:
        return _handle_approve(post, db)
    elif expected_action == ApprovalAction.REJECT:
        return _handle_reject(post, db)
    elif expected_action == ApprovalAction.EDIT:
        return _handle_edit(post, db)

    return False, "Unknown action", None


def _handle_approve(post: Post, db: Session) -> tuple[bool, str, Post]:
    """Approve and schedule a post."""
    settings = get_settings()

    # Calculate next publish time (10 AM Pacific, tomorrow if past 10 AM)
    import pytz

    tz = pytz.timezone(settings.timezone)
    now = datetime.now(tz)

    # Default to 10 AM tomorrow
    scheduled = now.replace(
        hour=settings.default_publish_hour,
        minute=settings.default_publish_minute,
        second=0,
        microsecond=0,
    )

    # If it's already past 10 AM, schedule for tomorrow
    if now.hour >= settings.default_publish_hour:
        scheduled += timedelta(days=1)

    post.status = PostStatus.SCHEDULED
    post.scheduled_at = scheduled.astimezone(timezone.utc)
    db.commit()

    # Schedule the publish job
    from publisher.scheduler import schedule_post

    schedule_post(post.id, post.scheduled_at)

    return True, f"Post approved and scheduled for {scheduled.strftime('%B %d at %I:%M %p')}", post


def _handle_reject(post: Post, db: Session) -> tuple[bool, str, Post]:
    """Reject a post."""
    post.status = PostStatus.REJECTED
    db.commit()

    return True, "Post has been rejected", post


def _handle_edit(post: Post, db: Session) -> tuple[bool, str, Post]:
    """Mark post for editing (redirect to dashboard)."""
    # Keep status as pending_approval
    return True, "Redirecting to editor", post


@router.get("/{action}/{token}")
async def approval_action(
    action: str,
    token: str,
    db: Session = Depends(get_db),
):
    """Handle approval action from email link."""
    settings = get_settings()

    success, message, post = handle_approval_action(token, action, db)

    if not success:
        return HTMLResponse(
            content=_error_html("Action Failed", message),
            status_code=400,
        )

    # For edit action, redirect to dashboard
    if action.lower() == "edit" and post:
        return RedirectResponse(
            url=f"{settings.base_url}/post/{post.id}",
            status_code=303,
        )

    return HTMLResponse(
        content=_success_html("Success", message),
        status_code=200,
    )
