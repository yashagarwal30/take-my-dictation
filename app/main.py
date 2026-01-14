"""
FastAPI application entry point for Take My Dictation.
Voice recording app with AI transcription and summaries.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.db.database import init_db, close_db
from app.api import recordings, transcriptions, summaries, admin, auth, payments, trials, users
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    # Startup
    print("🚀 Starting Take My Dictation API...")

    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"📁 Upload directory: {settings.UPLOAD_DIR}")

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Start background scheduler
    await start_scheduler()
    print("✅ Background scheduler started")

    yield

    # Shutdown
    print("👋 Shutting down...")
    await stop_scheduler()
    print("✅ Background scheduler stopped")
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(trials.router)
app.include_router(payments.router)
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(recordings.router, prefix="/recordings", tags=["Recordings"])
app.include_router(transcriptions.router, prefix="/transcriptions", tags=["Transcriptions"])
app.include_router(summaries.router, prefix="/summaries", tags=["Summaries"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "docs": "/docs",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
