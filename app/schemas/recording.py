"""
Pydantic schemas for Recording endpoints.
Request and response models for API validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.recording import RecordingStatus


class RecordingBase(BaseModel):
    """Base schema for recordings."""
    pass


class RecordingCreate(RecordingBase):
    """Schema for creating a recording (internal use)."""
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    format: str
    duration: Optional[float] = None


class RecordingUpdate(BaseModel):
    """Schema for updating a recording."""
    status: Optional[RecordingStatus] = None
    duration: Optional[float] = None


class RecordingResponse(RecordingBase):
    """Schema for recording response."""
    id: str
    filename: str
    original_filename: str
    file_size: int
    duration: Optional[float]
    format: str
    status: RecordingStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecordingListResponse(BaseModel):
    """Schema for list of recordings."""
    recordings: list[RecordingResponse]
    total: int
    page: int
    page_size: int
