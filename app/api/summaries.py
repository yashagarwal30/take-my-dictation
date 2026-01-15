"""
Summary API endpoints.
Handles AI-powered summary generation.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.recording import Recording
from app.models.transcription import Transcription
from app.models.summary import Summary, SummaryFormat
from app.models.user import User
from app.schemas.summary import SummaryGenerate, SummaryRegenerate, SummaryRename, SummaryResponse
from app.services.summary_service import SummaryService
from app.services.export_service import export_service
from app.core.dependencies import get_current_user, require_can_regenerate
from typing import Optional, List

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
        # If custom prompt is provided or explicitly requested, regenerate
        if request.custom_prompt:
            try:
                summary_service = SummaryService()
                updated_summary = await summary_service.regenerate_summary(
                    existing,
                    transcription.text,
                    db,
                    custom_prompt=request.custom_prompt
                )
                await db.refresh(updated_summary)
                return updated_summary
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Summary regeneration failed: {str(e)}"
                )
        else:
            # Return existing summary without error
            return existing

    try:
        # Generate summary using service
        summary_service = SummaryService()
        summary = await summary_service.generate_summary(
            transcription.text,
            request.recording_id,
            transcription.id,
            db,
            format=request.format,
            custom_prompt=request.custom_prompt
        )

        await db.refresh(summary)
        return summary

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summary generation failed: {str(e)}"
        )


@router.get("/", response_model=List[SummaryResponse])
async def list_summaries(
    format: Optional[SummaryFormat] = None,
    is_saved: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List summaries with optional filters.

    Args:
        format: Optional filter by summary format
        is_saved: Optional filter by saved status
        limit: Maximum number of summaries to return
        offset: Number of summaries to skip
        db: Database session

    Returns:
        List of summaries
    """
    query = select(Summary)

    # Apply filters
    if format is not None:
        query = query.filter(Summary.format == format)
    if is_saved is not None:
        query = query.filter(Summary.is_saved == is_saved)

    # Order by most recent first
    query = query.order_by(Summary.created_at.desc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    summaries = result.scalars().all()

    return summaries


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


@router.post("/regenerate", response_model=SummaryResponse, status_code=201)
async def regenerate_summary_from_audio(
    recording_id: str,
    request: SummaryRegenerate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_regenerate)
):
    """
    Regenerate summary from existing audio (requires audio retention).

    This endpoint creates a NEW summary from the original audio file.
    Requires that the audio file still exists (Pro users with audio retention enabled).

    Args:
        recording_id: Recording ID
        request: Regeneration request with format and custom prompt
        db: Database session

    Returns:
        New summary with different format

    Raises:
        HTTPException: If recording not found or audio not available
    """
    # Get recording
    result = await db.execute(
        select(Recording).filter(Recording.id == recording_id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Check if audio is still available for regeneration
    if not recording.can_regenerate:
        raise HTTPException(
            status_code=403,
            detail="Audio file no longer available. Regeneration requires audio retention (Pro feature)."
        )

    # Get transcription
    result = await db.execute(
        select(Transcription).filter(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    try:
        # Generate NEW summary with different format
        summary_service = SummaryService()
        new_summary = await summary_service.generate_summary(
            transcription.text,
            recording_id,
            transcription.id,
            db,
            format=request.format or SummaryFormat.QUICK_SUMMARY,
            custom_prompt=request.custom_prompt
        )

        await db.refresh(new_summary)
        return new_summary

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summary regeneration failed: {str(e)}"
        )


@router.put("/{summary_id}/regenerate", response_model=SummaryResponse)
async def update_existing_summary(
    summary_id: str,
    request: SummaryRegenerate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing summary with new format or custom prompt.

    This endpoint UPDATES the existing summary record.

    Args:
        summary_id: Summary ID
        request: Regeneration request
        db: Database session

    Returns:
        Updated summary

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
            format=request.format,
            custom_prompt=request.custom_prompt
        )

        await db.refresh(updated_summary)
        return updated_summary

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summary regeneration failed: {str(e)}"
        )


@router.put("/{summary_id}/rename", response_model=SummaryResponse)
async def rename_summary(
    summary_id: str,
    request: SummaryRename,
    db: AsyncSession = Depends(get_db)
):
    """
    Rename a summary with a custom name.

    Args:
        summary_id: Summary ID
        request: Rename request with new custom name
        db: Database session

    Returns:
        Updated summary

    Raises:
        HTTPException: If summary not found
    """
    result = await db.execute(
        select(Summary).filter(Summary.id == summary_id)
    )
    summary = result.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    # Update custom name
    summary.custom_name = request.custom_name
    await db.commit()
    await db.refresh(summary)

    return summary


@router.get("/{recording_id}/export/word")
async def export_word(
    recording_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Export transcription and summary as Word document.

    Args:
        recording_id: Recording ID
        db: Database session

    Returns:
        Word document file

    Raises:
        HTTPException: If transcription not found
    """
    # Get recording
    recording_result = await db.execute(
        select(Recording).filter(Recording.id == recording_id)
    )
    recording = recording_result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Get transcription
    transcription_result = await db.execute(
        select(Transcription).filter(Transcription.recording_id == recording_id)
    )
    transcription = transcription_result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Get summary (optional)
    summary_result = await db.execute(
        select(Summary).filter(Summary.recording_id == recording_id)
    )
    summary = summary_result.scalar_one_or_none()

    # Generate Word document
    # Use custom name if available, otherwise use recording filename
    display_name = summary.custom_name if (summary and summary.custom_name) else recording.original_filename

    buffer = export_service.create_docx(
        transcription_text=transcription.text,
        summary_text=summary.summary_text if summary else None,
        recording_filename=display_name,
        created_at=recording.created_at
    )

    # Use custom name for the exported file if available
    base_name = summary.custom_name if (summary and summary.custom_name) else recording.original_filename.rsplit('.', 1)[0]
    filename = f"{base_name}_transcript.docx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{recording_id}/export/pdf")
async def export_pdf(
    recording_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Export transcription and summary as PDF document.

    Args:
        recording_id: Recording ID
        db: Database session

    Returns:
        PDF document file

    Raises:
        HTTPException: If transcription not found
    """
    # Get recording
    recording_result = await db.execute(
        select(Recording).filter(Recording.id == recording_id)
    )
    recording = recording_result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Get transcription
    transcription_result = await db.execute(
        select(Transcription).filter(Transcription.recording_id == recording_id)
    )
    transcription = transcription_result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Get summary (optional)
    summary_result = await db.execute(
        select(Summary).filter(Summary.recording_id == recording_id)
    )
    summary = summary_result.scalar_one_or_none()

    # Generate PDF document
    # Use custom name if available, otherwise use recording filename
    display_name = summary.custom_name if (summary and summary.custom_name) else recording.original_filename

    buffer = export_service.create_pdf(
        transcription_text=transcription.text,
        summary_text=summary.summary_text if summary else None,
        recording_filename=display_name,
        created_at=recording.created_at
    )

    # Use custom name for the exported file if available
    base_name = summary.custom_name if (summary and summary.custom_name) else recording.original_filename.rsplit('.', 1)[0]
    filename = f"{base_name}_transcript.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
