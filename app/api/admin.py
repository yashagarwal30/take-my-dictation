"""
Admin API endpoints.
Health checks and statistics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.models.recording import Recording
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        API health status
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Get API usage statistics.

    Args:
        db: Database session

    Returns:
        Usage statistics
    """
    # Count recordings
    recordings_count = await db.scalar(
        select(func.count()).select_from(Recording)
    )

    # Count transcriptions
    transcriptions_count = await db.scalar(
        select(func.count()).select_from(Transcription)
    )

    # Count summaries
    summaries_count = await db.scalar(
        select(func.count()).select_from(Summary)
    )

    # Get total storage size
    total_size_result = await db.execute(
        select(func.sum(Recording.file_size))
    )
    total_size = total_size_result.scalar() or 0

    # Get total duration
    total_duration_result = await db.execute(
        select(func.sum(Recording.duration))
    )
    total_duration = total_duration_result.scalar() or 0

    return {
        "recordings": {
            "total": recordings_count or 0,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_duration_seconds": round(total_duration, 2),
            "total_duration_minutes": round(total_duration / 60, 2)
        },
        "transcriptions": {
            "total": transcriptions_count or 0
        },
        "summaries": {
            "total": summaries_count or 0
        }
    }
