"""
Recording API endpoints.
Handles audio file uploads, retrieval, and management.
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import os
import uuid
from datetime import datetime

from app.db.database import get_db
from app.models.recording import Recording, RecordingStatus
from app.schemas.recording import RecordingResponse, RecordingListResponse
from app.core.config import settings
from app.services.audio_service import AudioService

router = APIRouter()


@router.post("/upload", response_model=RecordingResponse, status_code=201)
async def upload_recording(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an audio recording.

    Args:
        file: Audio file to upload
        db: Database session

    Returns:
        Recording metadata

    Raises:
        HTTPException: If file format is invalid or upload fails
    """
    # Validate file format
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in settings.allowed_formats_list:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed formats: {', '.join(settings.allowed_formats_list)}"
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    try:
        # Save file to disk
        audio_service = AudioService()
        file_size = await audio_service.save_uploaded_file(file, file_path)

        # Get audio duration
        duration = await audio_service.get_audio_duration(file_path)

        # Create database record
        recording = Recording(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            duration=duration,
            format=file_extension,
            status=RecordingStatus.COMPLETED
        )

        db.add(recording)
        await db.commit()
        await db.refresh(recording)

        return recording

    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to upload recording: {str(e)}")


@router.get("/", response_model=RecordingListResponse)
async def list_recordings(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[RecordingStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all recordings with pagination.

    Args:
        page: Page number (starts at 1)
        page_size: Number of items per page
        status: Optional status filter
        db: Database session

    Returns:
        List of recordings with pagination info
    """
    # Build query
    query = select(Recording)
    if status:
        query = query.filter(Recording.status == status)

    # Get total count
    count_query = select(func.count()).select_from(Recording)
    if status:
        count_query = count_query.filter(Recording.status == status)
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.order_by(Recording.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    recordings = result.scalars().all()

    return RecordingListResponse(
        recordings=recordings,
        total=total or 0,
        page=page,
        page_size=page_size
    )


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific recording by ID.

    Args:
        recording_id: Recording ID
        db: Database session

    Returns:
        Recording metadata

    Raises:
        HTTPException: If recording not found
    """
    result = await db.execute(
        select(Recording).filter(Recording.id == recording_id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    return recording


@router.get("/{recording_id}/audio")
async def get_recording_audio(
    recording_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream the audio file for a recording.

    Args:
        recording_id: Recording ID
        db: Database session

    Returns:
        Audio file

    Raises:
        HTTPException: If recording not found or file missing
    """
    result = await db.execute(
        select(Recording).filter(Recording.id == recording_id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not os.path.exists(recording.file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        recording.file_path,
        media_type=f"audio/{recording.format}",
        filename=recording.original_filename
    )


@router.delete("/{recording_id}", status_code=204)
async def delete_recording(
    recording_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a recording and its associated file.

    Args:
        recording_id: Recording ID
        db: Database session

    Raises:
        HTTPException: If recording not found
    """
    result = await db.execute(
        select(Recording).filter(Recording.id == recording_id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Delete file from disk
    if os.path.exists(recording.file_path):
        os.remove(recording.file_path)

    # Delete from database
    await db.delete(recording)
    await db.commit()

    return None
