"""
Transcription API endpoints.
Handles transcription creation and retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.recording import Recording, RecordingStatus
from app.models.transcription import Transcription
from app.schemas.transcription import TranscriptionCreate, TranscriptionResponse, TranscriptionUpdate
from app.services.transcription_service import TranscriptionService

router = APIRouter()


@router.post("/create", response_model=TranscriptionResponse, status_code=201)
async def create_transcription(
    request: TranscriptionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a transcription for a recording.

    Args:
        request: Transcription creation request
        background_tasks: Background task manager
        db: Database session

    Returns:
        Transcription result

    Raises:
        HTTPException: If recording not found or transcription already exists
    """
    # Check if recording exists
    result = await db.execute(
        select(Recording).filter(Recording.id == request.recording_id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Check if transcription already exists
    result = await db.execute(
        select(Transcription).filter(Transcription.recording_id == request.recording_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Transcription already exists for this recording"
        )

    # Update recording status
    recording.status = RecordingStatus.PROCESSING
    await db.commit()

    try:
        # Create transcription using service
        transcription_service = TranscriptionService()
        transcription = await transcription_service.transcribe_audio(
            recording.file_path,
            recording.id,
            db
        )

        # Update recording status
        recording.status = RecordingStatus.COMPLETED
        await db.commit()
        await db.refresh(transcription)

        return transcription

    except Exception as e:
        # Update recording status to failed
        recording.status = RecordingStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@router.get("/{recording_id}", response_model=TranscriptionResponse)
async def get_transcription(
    recording_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get transcription for a recording.

    Args:
        recording_id: Recording ID
        db: Database session

    Returns:
        Transcription data

    Raises:
        HTTPException: If transcription not found
    """
    result = await db.execute(
        select(Transcription).filter(Transcription.recording_id == recording_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    return transcription


@router.put("/{transcription_id}", response_model=TranscriptionResponse)
async def update_transcription(
    transcription_id: str,
    request: TranscriptionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update transcription text (manual corrections).

    Args:
        transcription_id: Transcription ID
        request: Updated transcription data
        db: Database session

    Returns:
        Updated transcription

    Raises:
        HTTPException: If transcription not found
    """
    result = await db.execute(
        select(Transcription).filter(Transcription.id == transcription_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Update text
    transcription.text = request.text
    await db.commit()
    await db.refresh(transcription)

    return transcription
