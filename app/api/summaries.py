"""
Summary API endpoints.
Handles AI-powered summary generation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.schemas.summary import SummaryGenerate, SummaryResponse
from app.services.summary_service import SummaryService

router = APIRouter()


@router.post("/generate", response_model=SummaryResponse, status_code=201)
async def generate_summary(
    request: SummaryGenerate,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI summary for a recording.

    Args:
        request: Summary generation request
        db: Database session

    Returns:
        Generated summary

    Raises:
        HTTPException: If transcription not found or summary already exists
    """
    # Check if transcription exists
    result = await db.execute(
        select(Transcription).filter(Transcription.recording_id == request.recording_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(
            status_code=404,
            detail="Transcription not found. Please create transcription first."
        )

    # Check if summary already exists
    result = await db.execute(
        select(Summary).filter(Summary.recording_id == request.recording_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Summary already exists for this recording. Use regenerate endpoint to create a new one."
        )

    try:
        # Generate summary using service
        summary_service = SummaryService()
        summary = await summary_service.generate_summary(
            transcription.text,
            request.recording_id,
            transcription.id,
            db,
            custom_prompt=request.custom_prompt
        )

        await db.refresh(summary)
        return summary

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summary generation failed: {str(e)}"
        )


@router.get("/{recording_id}", response_model=SummaryResponse)
async def get_summary(
    recording_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary for a recording.

    Args:
        recording_id: Recording ID
        db: Database session

    Returns:
        Summary data

    Raises:
        HTTPException: If summary not found
    """
    result = await db.execute(
        select(Summary).filter(Summary.recording_id == recording_id)
    )
    summary = result.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    return summary


@router.put("/{summary_id}/regenerate", response_model=SummaryResponse)
async def regenerate_summary(
    summary_id: str,
    custom_prompt: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate an existing summary.

    Args:
        summary_id: Summary ID
        custom_prompt: Optional custom instructions
        db: Database session

    Returns:
        Regenerated summary

    Raises:
        HTTPException: If summary not found
    """
    result = await db.execute(
        select(Summary).filter(Summary.id == summary_id)
    )
    summary = result.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    # Get transcription
    result = await db.execute(
        select(Transcription).filter(Transcription.id == summary.transcription_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    try:
        # Regenerate summary
        summary_service = SummaryService()
        updated_summary = await summary_service.regenerate_summary(
            summary,
            transcription.text,
            db,
            custom_prompt=custom_prompt
        )

        await db.refresh(updated_summary)
        return updated_summary

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summary regeneration failed: {str(e)}"
        )
