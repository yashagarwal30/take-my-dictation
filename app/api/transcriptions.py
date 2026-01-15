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
from app.services.usage_tracking_service import UsageTrackingService

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

    # Check usage limit BEFORE starting transcription
    if recording.user_id:
        from app.services.usage_tracking_service import UsageTrackingService
        usage_service = UsageTrackingService()
        usage_info = await usage_service.check_usage_limit(recording.user_id, db)

        if usage_info["limit_exceeded"]:
            # Generate appropriate error message
            if usage_info["user_type"] == "trial":
                raise HTTPException(
                    status_code=403,
                    detail="You've used your free 10 minutes. Subscribe to continue recording."
                )
            else:
                # Check if this is a FREE tier user (no subscription)
                if usage_info["monthly_hours_limit"] <= 0:
                    raise HTTPException(
                        status_code=403,
                        detail="Please subscribe to start recording. Choose from Basic ($9.99/month) or Pro ($19.99/month) plans."
                    )

                # Paid user exceeded monthly limit
                reset_date = usage_info.get("reset_date")
                reset_str = reset_date.strftime("%B %d, %Y") if reset_date else "next month"
                raise HTTPException(
                    status_code=403,
                    detail=f"Monthly limit reached. Resets on {reset_str}."
                )

    # Check if transcription already exists
    result = await db.execute(
        select(Transcription).filter(Transcription.recording_id == request.recording_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # If transcription exists, update recording status and return existing transcription
        if recording.status != RecordingStatus.COMPLETED:
            recording.status = RecordingStatus.COMPLETED
            await db.commit()
        return existing

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

        # Track usage for non-trial or paid users
        usage_warning = None
        usage_info_dict = None

        if recording.user_id and recording.duration:
            try:
                usage_service = UsageTrackingService()
                usage_result = await usage_service.track_recording_usage(
                    recording.user_id,
                    recording.duration,
                    db
                )
                print(f"✅ Usage tracked: {usage_result}")

                # Get usage warnings
                usage_check = await usage_service.check_usage_limit(recording.user_id, db)
                usage_warning = await usage_service.get_usage_warning_message(usage_check)

                # Build usage info
                if usage_check["user_type"] == "trial":
                    usage_info_dict = {
                        "trial_minutes_used": usage_check["trial_minutes_used"],
                        "trial_minutes_remaining": usage_check["trial_minutes_remaining"]
                    }
                else:
                    usage_info_dict = {
                        "monthly_hours_used": usage_check["monthly_hours_used"],
                        "monthly_hours_limit": usage_check["monthly_hours_limit"],
                        "monthly_hours_remaining": usage_check["monthly_hours_remaining"],
                        "usage_percentage": usage_check["usage_percentage"]
                    }

            except Exception as usage_error:
                # Don't fail transcription if usage tracking fails
                print(f"⚠️  Usage tracking failed: {usage_error}")

        # Prepare response with usage information
        response_data = {
            "id": transcription.id,
            "recording_id": transcription.recording_id,
            "text": transcription.text,
            "language": transcription.language,
            "confidence": transcription.confidence,
            "provider": transcription.provider,
            "created_at": transcription.created_at,
            "updated_at": transcription.updated_at,
            "usage_warning": usage_warning,
            "usage_info": usage_info_dict
        }

        return response_data

    except Exception as e:
        # Rollback the session to clear any pending transaction state
        await db.rollback()

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
