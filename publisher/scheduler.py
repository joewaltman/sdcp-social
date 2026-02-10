"""APScheduler configuration for scheduled publishing."""

import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session

from config import get_settings
from models import Post, PostStatus
from models.database import SessionLocal

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        settings = get_settings()
        _scheduler = BackgroundScheduler(
            jobstores={
                "default": SQLAlchemyJobStore(url=settings.database_url),
            },
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 3600,  # 1 hour grace period
            },
        )
    return _scheduler


def start_scheduler():
    """Start the scheduler if not already running."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown complete")


def publish_post_job(post_id: int):
    """Job function to publish a post.

    This runs in the scheduler's background thread.
    """
    from publisher.facebook import FacebookPublisher
    from publisher.instagram import InstagramPublisher

    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            logger.error(f"Post {post_id} not found for publishing")
            return

        if post.status != PostStatus.SCHEDULED:
            logger.warning(f"Post {post_id} is not scheduled (status: {post.status})")
            return

        logger.info(f"Starting publish for post {post_id}")

        # Get photo paths
        photo_paths = [photo.storage_path for photo in post.photos]

        errors = []

        # Publish to Instagram
        if post.instagram_caption:
            try:
                ig_publisher = InstagramPublisher()
                ig_post_id = ig_publisher.publish_post(
                    photo_paths=photo_paths,
                    caption=post.instagram_caption,
                    hashtags=post.hashtags,
                )
                post.instagram_post_id = ig_post_id
                logger.info(f"Published to Instagram: {ig_post_id}")
            except Exception as e:
                logger.error(f"Instagram publish failed for post {post_id}: {e}")
                errors.append(f"Instagram: {e}")

        # Publish to Facebook
        if post.facebook_caption:
            try:
                fb_publisher = FacebookPublisher()
                fb_post_id = fb_publisher.publish_post(
                    photo_paths=photo_paths,
                    message=post.facebook_caption,
                )
                post.facebook_post_id = fb_post_id
                logger.info(f"Published to Facebook: {fb_post_id}")
            except Exception as e:
                logger.error(f"Facebook publish failed for post {post_id}: {e}")
                errors.append(f"Facebook: {e}")

        # Update status
        if errors:
            post.status = PostStatus.FAILED
            post.last_error = "\n".join(errors)
        else:
            post.status = PostStatus.PUBLISHED
            post.published_at = datetime.now(timezone.utc)
            post.last_error = None

        db.commit()
        logger.info(f"Post {post_id} publish complete, status: {post.status}")

    except Exception as e:
        logger.error(f"Unexpected error publishing post {post_id}: {e}")
        try:
            post.status = PostStatus.FAILED
            post.last_error = str(e)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


def schedule_post(post_id: int, publish_at: datetime) -> str:
    """Schedule a post for publishing.

    Returns the job ID.
    """
    scheduler = get_scheduler()

    # Ensure scheduler is running
    if not scheduler.running:
        start_scheduler()

    job_id = f"publish_post_{post_id}"

    # Remove existing job if any
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    # Schedule new job
    job = scheduler.add_job(
        publish_post_job,
        trigger=DateTrigger(run_date=publish_at),
        args=[post_id],
        id=job_id,
        name=f"Publish post {post_id}",
        replace_existing=True,
    )

    logger.info(f"Scheduled post {post_id} for {publish_at}")
    return job.id


def unschedule_post(post_id: int) -> bool:
    """Remove a scheduled publish job.

    Returns True if job was removed, False if not found.
    """
    scheduler = get_scheduler()
    job_id = f"publish_post_{post_id}"

    try:
        scheduler.remove_job(job_id)
        logger.info(f"Unscheduled post {post_id}")
        return True
    except Exception:
        return False


def get_scheduled_jobs() -> list[dict]:
    """Get list of scheduled publish jobs."""
    scheduler = get_scheduler()
    jobs = []

    for job in scheduler.get_jobs():
        if job.id.startswith("publish_post_"):
            jobs.append({
                "id": job.id,
                "post_id": int(job.id.replace("publish_post_", "")),
                "next_run": job.next_run_time,
                "name": job.name,
            })

    return jobs
