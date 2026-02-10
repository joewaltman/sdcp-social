"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from approval.approval_handler import router as approval_router
from config import get_settings
from dashboard.app import router as dashboard_router
from intake.webhook import router as webhook_router
from publisher.scheduler import shutdown_scheduler, start_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting SDCP Social Post Generator")

    settings = get_settings()

    # Ensure upload directory exists
    settings.photo_storage_path.mkdir(parents=True, exist_ok=True)

    # Start the scheduler
    start_scheduler()

    yield

    # Shutdown
    logger.info("Shutting down...")
    shutdown_scheduler()


app = FastAPI(
    title="SDCP Social Post Generator",
    description="AI-powered social media post generation for San Diego Custom Painting",
    version="1.0.0",
    lifespan=lifespan,
)


# Include routers
app.include_router(webhook_router)
app.include_router(approval_router)
app.include_router(dashboard_router)


# Mount static files for uploaded photos
@app.on_event("startup")
async def mount_uploads():
    """Mount uploads directory as static files."""
    settings = get_settings()
    uploads_path = settings.photo_storage_path
    uploads_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


# Mount dashboard static files if they exist
dashboard_static = Path(__file__).parent / "dashboard" / "static"
if dashboard_static.exists():
    app.mount("/static", StaticFiles(directory=str(dashboard_static)), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sdcp-social"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
