"""Postmark inbound webhook endpoint."""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from config import get_settings
from generator.post_generator import PostGenerator
from intake.email_parser import EmailParser
from intake.photo_processor import PhotoProcessor
from models import Post, PostStatus, get_db
from models.photo import Photo
from schemas.postmark import PostmarkInboundEmail

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

email_parser = EmailParser()
photo_processor = PhotoProcessor()


async def process_email_task(
    email: PostmarkInboundEmail,
    db: Session,
) -> Optional[int]:
    """Background task to process an inbound email.

    Returns the post ID if successful.
    """
    settings = get_settings()

    # Parse email content
    parsed = email_parser.parse(email)
    logger.info(
        f"Processing email from {parsed.sender_email}: "
        f"location={parsed.project_location}, type={parsed.project_type}"
    )

    # Check for duplicate (by message ID)
    existing = db.query(Post).filter(Post.source_message_id == parsed.message_id).first()
    if existing:
        logger.warning(f"Duplicate email received: {parsed.message_id}")
        return existing.id

    # Process photo attachments
    image_attachments = email.get_image_attachments()
    if not image_attachments:
        logger.warning(f"No images in email from {parsed.sender_email}")
        return None

    processed_photos = photo_processor.process_attachments(image_attachments)
    if not processed_photos:
        logger.warning(f"No valid photos after processing from {parsed.sender_email}")
        return None

    # Create post record
    post = Post(
        source_email=parsed.sender_email,
        source_message_id=parsed.message_id,
        project_location=parsed.project_location,
        project_type=parsed.project_type,
        additional_context=parsed.additional_context,
        status=PostStatus.DRAFT,
    )
    db.add(post)
    db.flush()  # Get the post ID

    # Create photo records
    for i, photo_data in enumerate(processed_photos):
        photo = Photo(
            post_id=post.id,
            filename=photo_data.filename,
            storage_path=photo_data.storage_path,
            content_type=photo_data.content_type,
            file_size=photo_data.file_size,
            width=photo_data.width,
            height=photo_data.height,
            display_order=i,
            is_primary=(i == 0),
        )
        db.add(photo)

    db.commit()
    logger.info(f"Created post {post.id} with {len(processed_photos)} photos")

    # Generate AI content
    try:
        generator = PostGenerator()

        # Prepare image data for Claude
        image_data = [
            (photo.base64_data, photo.content_type) for photo in processed_photos
        ]

        generated = generator.generate_post(
            project_location=parsed.project_location,
            project_type=parsed.project_type,
            additional_context=parsed.additional_context,
            image_data=image_data,
        )

        # Update post with generated content
        post.instagram_caption = generated.instagram_caption
        post.facebook_caption = generated.facebook_caption
        post.hashtags = generated.hashtags
        post.status = PostStatus.PENDING_APPROVAL

        # Store AI descriptions on photos
        for i, photo in enumerate(post.photos):
            if i < len(generated.photo_descriptions):
                photo.ai_description = generated.photo_descriptions[i]

        db.commit()
        logger.info(f"Generated content for post {post.id}")

        # Send approval email
        from approval.email_sender import send_approval_email

        await send_approval_email(post.id, db)

    except Exception as e:
        logger.error(f"Error generating content for post {post.id}: {e}")
        post.status = PostStatus.DRAFT
        post.last_error = str(e)
        db.commit()

    return post.id


@router.post("/inbound")
async def handle_inbound_email(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Handle inbound email webhook from Postmark."""
    try:
        payload = await request.json()
        email = PostmarkInboundEmail(**payload)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Check for image attachments
    image_attachments = email.get_image_attachments()
    if not image_attachments:
        logger.info(f"No images in email from {email.get_sender_email()}, ignoring")
        return {"status": "ignored", "reason": "no_images"}

    # Process in background to respond quickly to Postmark
    post_id = await process_email_task(email, db)

    if post_id:
        return {"status": "accepted", "post_id": post_id}
    else:
        return {"status": "ignored", "reason": "processing_failed"}


@router.get("/health")
async def webhook_health():
    """Health check endpoint for the webhook."""
    return {"status": "ok"}
