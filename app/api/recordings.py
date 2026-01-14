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
from app.models.user import User
from app.schemas.recording import RecordingResponse, RecordingListResponse, RecordingUploadResponse
from app.core.config import settings
from app.core.dependencies import get_optional_user, check_usage_limit, get_current_user, require_pro
from app.services.audio_service import AudioService
from app.services.usage_tracking_service import UsageTrackingService
from app.services.audio_retention_service import AudioRetentionService

router = APIRouter()


@router.post("/upload", response_model=RecordingUploadResponse, status_code=201)
async def upload_recording(
    file: UploadFile = File(...),
    custom_name: Optional[str] = Query(None, description="Custom name for the recording"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Upload an audio recording.

    Checks usage limits if user is authenticated.

    Args:
        file: Audio file to upload
        db: Database session
        current_user: Optional authenticated user

    Returns:
        Recording metadata

    Raises:
        HTTPException: If file format is invalid, upload fails, or usage limit exceeded
    """
    # Check usage limit if user is authenticated
    if current_user:
        from app.services.usage_tracking_service import UsageTrackingService
        usage_service = UsageTrackingService()
        usage_info = await usage_service.check_usage_limit(current_user.id, db)

        if usage_info["limit_exceeded"]:
            # Generate appropriate error message
            if usage_info["user_type"] == "trial":
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Trial limit exceeded",
                        "message": "You've used your free 10 minutes. Subscribe to continue recording.",
                        "trial_minutes_used": usage_info["trial_minutes_used"],
                        "upgrade_required": True
                    }
                )
            else:
                # Paid user exceeded monthly limit
                reset_date = usage_info.get("reset_date")
                reset_str = reset_date.strftime("%B %d, %Y") if reset_date else "next month"
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Monthly limit exceeded",
                        "message": f"Monthly limit reached. Resets on {reset_str}.",
                        "monthly_hours_used": usage_info["monthly_hours_used"],
                        "monthly_hours_limit": usage_info["monthly_hours_limit"],
                        "reset_date": reset_str,
                        "upgrade_available": usage_info["subscription_tier"] == "basic"
                    }
                )

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
            user_id=current_user.id if current_user else None,
            filename=unique_filename,
            original_filename=file.filename,
            custom_name=custom_name if custom_name else None,
            file_path=file_path,
            file_size=file_size,
            duration=duration,
            format=file_extension,
            status=RecordingStatus.COMPLETED
        )

        db.add(recording)
        await db.commit()
        await db.refresh(recording)

        # Set audio retention policy based on user tier
        retention_service = AudioRetentionService()
        retention_info = await retention_service.set_retention_policy(
            recording,
            current_user,
            db
        )
        print(f"📁 Audio retention set: {retention_info}")

        # Prepare response with usage information
        response_data = {
            "id": recording.id,
            "filename": recording.filename,
            "original_filename": recording.original_filename,
            "file_size": recording.file_size,
            "duration": recording.duration,
            "format": recording.format,
            "status": recording.status,
            "created_at": recording.created_at,
            "updated_at": recording.updated_at
        }

        # Add usage warnings if user is authenticated
        if current_user:
            usage_service = UsageTrackingService()
            usage_check = await usage_service.check_usage_limit(current_user.id, db)
            warning = await usage_service.get_usage_warning_message(usage_check)

            if warning:
                response_data["usage_warning"] = warning

            # Include basic usage info
            if usage_check["user_type"] == "trial":
                response_data["usage_info"] = {
                    "trial_minutes_used": usage_check["trial_minutes_used"],
                    "trial_minutes_remaining": usage_check["trial_minutes_remaining"]
                }
            else:
                response_data["usage_info"] = {
                    "monthly_hours_used": usage_check["monthly_hours_used"],
                    "monthly_hours_limit": usage_check["monthly_hours_limit"],
                    "monthly_hours_remaining": usage_check["monthly_hours_remaining"],
                    "usage_percentage": usage_check["usage_percentage"]
                }

        # Add retention info
        retention_status = await retention_service.check_retention_status(recording.id, db)
        response_data["retention_info"] = {
            "audio_retention_enabled": retention_status["audio_retention_enabled"],
            "days_remaining": retention_status["days_remaining"],
            "can_regenerate": retention_status["can_regenerate"]
        }
        if retention_status.get("audio_delete_at"):
            response_data["retention_info"]["audio_delete_at"] = retention_status["audio_delete_at"]

        return response_data

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
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    List recordings with pagination.

    If user is authenticated, returns only their recordings.
    If user is not authenticated, returns all recordings.

    Args:
        page: Page number (starts at 1)
        page_size: Number of items per page
        status: Optional status filter
        db: Database session
        current_user: Optional authenticated user

    Returns:
        List of recordings with pagination info
    """
    # Build query - filter by user if authenticated
    query = select(Recording)
    if current_user:
        query = query.filter(Recording.user_id == current_user.id)
    if status:
        query = query.filter(Recording.status == status)

    # Get total count
    count_query = select(func.count()).select_from(Recording)
    if current_user:
        count_query = count_query.filter(Recording.user_id == current_user.id)
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


@router.put("/{recording_id}/rename", response_model=RecordingResponse)
async def rename_recording(
    recording_id: str,
    custom_name: str = Query(..., description="New custom name for the recording", min_length=1, max_length=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rename a recording with a custom name.

    Requires authentication. User can only rename their own recordings.

    Args:
        recording_id: Recording ID
        custom_name: New custom name
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated recording

    Raises:
        HTTPException: If recording not found or user doesn't own it
    """
    result = await db.execute(
        select(Recording).filter(Recording.id == recording_id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Check if user owns this recording
    if recording.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to rename this recording"
        )

    # Update custom name
    recording.custom_name = custom_name.strip()
    await db.commit()
    await db.refresh(recording)

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


@router.get("/{recording_id}/retention")
async def get_retention_status(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audio retention status for a recording.

    Args:
        recording_id: Recording ID
        db: Database session
        current_user: Authenticated user

    Returns:
        Retention status information

    Raises:
        HTTPException: If recording not found or unauthorized
    """
    # Get recording
    result = await db.execute(
        select(Recording).filter(Recording.id == recording_id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Check ownership
    if recording.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get retention status
    retention_service = AudioRetentionService()
    status = await retention_service.check_retention_status(recording_id, db)

    return status


@router.post("/{recording_id}/retain")
async def enable_audio_retention(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_pro)
):
    """
    Enable 10-day audio retention for a recording (Pro users only).

    Args:
        recording_id: Recording ID
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated retention information

    Raises:
        HTTPException: If user is not Pro tier or recording not found
    """
    try:
        retention_service = AudioRetentionService()
        result = await retention_service.enable_retention(
            recording_id,
            current_user,
            db
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{recording_id}/audio")
async def delete_audio_file(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually delete audio file for a recording.

    Keeps transcription and summary but removes audio file.
    After deletion, summary cannot be regenerated.

    Args:
        recording_id: Recording ID
        db: Database session
        current_user: Authenticated user

    Returns:
        Deletion result

    Raises:
        HTTPException: If recording not found or unauthorized
    """
    try:
        retention_service = AudioRetentionService()
        result = await retention_service.delete_audio_file(
            recording_id,
            current_user,
            db,
            force=False
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
