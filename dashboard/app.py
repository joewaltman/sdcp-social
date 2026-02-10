"""Dashboard routes for post management."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import get_settings
from dashboard.auth import (
    clear_session_cookie,
    get_current_user,
    require_auth,
    set_session_cookie,
    verify_password,
)
from models import Post, PostStatus, get_db

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="dashboard/templates")


def _format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if not dt:
        return "—"
    settings = get_settings()
    import pytz

    tz = pytz.timezone(settings.timezone)
    local = dt.astimezone(tz) if dt.tzinfo else dt
    return local.strftime("%b %d, %Y %I:%M %p")


def _status_badge(status: PostStatus) -> tuple[str, str]:
    """Get badge color and label for status."""
    badges = {
        PostStatus.DRAFT: ("bg-secondary", "Draft"),
        PostStatus.PENDING_APPROVAL: ("bg-warning text-dark", "Pending"),
        PostStatus.APPROVED: ("bg-info", "Approved"),
        PostStatus.SCHEDULED: ("bg-primary", "Scheduled"),
        PostStatus.PUBLISHED: ("bg-success", "Published"),
        PostStatus.REJECTED: ("bg-danger", "Rejected"),
        PostStatus.FAILED: ("bg-danger", "Failed"),
    }
    return badges.get(status, ("bg-secondary", str(status.value)))


# Add template globals
templates.env.globals["format_datetime"] = _format_datetime
templates.env.globals["status_badge"] = _status_badge
templates.env.globals["PostStatus"] = PostStatus


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page."""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


@router.post("/login")
async def login(
    request: Request,
    password: str = Form(...),
):
    """Handle login form submission."""
    if verify_password(password):
        response = RedirectResponse(url="/", status_code=303)
        set_session_cookie(response)
        return response

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid password"},
        status_code=401,
    )


@router.get("/logout")
async def logout():
    """Log out and redirect to login."""
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response)
    return response


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    """Dashboard home - show post queue."""
    settings = get_settings()

    # Build query
    query = db.query(Post)

    if status:
        try:
            status_enum = PostStatus(status)
            query = query.filter(Post.status == status_enum)
        except ValueError:
            pass

    # Get posts ordered by created date
    posts = query.order_by(desc(Post.created_at)).limit(50).all()

    # Count by status
    status_counts = {}
    for s in PostStatus:
        status_counts[s.value] = db.query(Post).filter(Post.status == s).count()

    return templates.TemplateResponse(
        "queue.html",
        {
            "request": request,
            "posts": posts,
            "status_counts": status_counts,
            "current_status": status,
            "settings": settings,
        },
    )


@router.get("/post/{post_id}", response_class=HTMLResponse)
async def post_detail(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    """Show post detail/edit page."""
    settings = get_settings()

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return templates.TemplateResponse(
        "post_detail.html",
        {
            "request": request,
            "post": post,
            "settings": settings,
        },
    )


@router.post("/post/{post_id}")
async def update_post(
    request: Request,
    post_id: int,
    instagram_caption: str = Form(...),
    facebook_caption: str = Form(...),
    hashtags: str = Form(""),
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    """Update post captions."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.instagram_caption = instagram_caption
    post.facebook_caption = facebook_caption

    # Parse hashtags
    if hashtags.strip():
        parsed = [
            h.strip() if h.strip().startswith("#") else f"#{h.strip()}"
            for h in hashtags.replace(",", " ").split()
            if h.strip()
        ]
        post.hashtags = parsed
    else:
        post.hashtags = []

    db.commit()

    return RedirectResponse(url=f"/post/{post_id}", status_code=303)


@router.post("/post/{post_id}/approve")
async def approve_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    """Approve a post from the dashboard."""
    from approval.approval_handler import _handle_approve

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    success, message, _ = _handle_approve(post, db)
    return RedirectResponse(url=f"/post/{post_id}", status_code=303)


@router.post("/post/{post_id}/reject")
async def reject_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    """Reject a post from the dashboard."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = PostStatus.REJECTED
    db.commit()

    return RedirectResponse(url=f"/post/{post_id}", status_code=303)


@router.post("/post/{post_id}/regenerate")
async def regenerate_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    """Regenerate AI content for a post."""
    from generator.post_generator import PostGenerator

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    try:
        generator = PostGenerator()

        # Get photo paths
        settings = get_settings()
        image_paths = [
            settings.photo_storage_path / photo.storage_path for photo in post.photos
        ]

        generated = generator.generate_post(
            project_location=post.project_location,
            project_type=post.project_type,
            additional_context=post.additional_context,
            image_paths=image_paths,
        )

        post.instagram_caption = generated.instagram_caption
        post.facebook_caption = generated.facebook_caption
        post.hashtags = generated.hashtags

        for i, photo in enumerate(post.photos):
            if i < len(generated.photo_descriptions):
                photo.ai_description = generated.photo_descriptions[i]

        db.commit()

    except Exception as e:
        post.last_error = str(e)
        db.commit()

    return RedirectResponse(url=f"/post/{post_id}", status_code=303)


@router.get("/published", response_class=HTMLResponse)
async def published_posts(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    """Show published posts."""
    settings = get_settings()

    posts = (
        db.query(Post)
        .filter(Post.status == PostStatus.PUBLISHED)
        .order_by(desc(Post.published_at))
        .limit(50)
        .all()
    )

    return templates.TemplateResponse(
        "published.html",
        {
            "request": request,
            "posts": posts,
            "settings": settings,
        },
    )
