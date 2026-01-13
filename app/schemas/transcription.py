"""
Pydantic schemas for Transcription endpoints.
Request and response models for API validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TranscriptionCreate(BaseModel):
    """Schema for creating a transcription."""
    recording_id: str = Field(..., description="ID of the recording to transcribe")


class TranscriptionUpdate(BaseModel):
    """Schema for updating a transcription."""
    text: str = Field(..., description="Updated transcription text")


class TranscriptionResponse(BaseModel):
    """Schema for transcription response."""
    id: str
    recording_id: str
    text: str
    language: Optional[str]
    confidence: Optional[float]
    provider: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
