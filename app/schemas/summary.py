"""
Pydantic schemas for Summary endpoints.
Request and response models for API validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.summary import SummaryFormat


class SummaryGenerate(BaseModel):
    """Schema for generating a summary."""
    recording_id: str = Field(..., description="ID of the recording to summarize")
    format: Optional[SummaryFormat] = Field(SummaryFormat.QUICK_SUMMARY, description="Summary format type")
    custom_prompt: Optional[str] = Field(None, description="Custom instructions for summary generation")


class SummaryRegenerate(BaseModel):
    """Schema for regenerating a summary."""
    format: Optional[SummaryFormat] = Field(None, description="Optional new format (keeps existing if not provided)")
    custom_prompt: Optional[str] = Field(None, description="Custom instructions for summary generation")


class SummaryRename(BaseModel):
    """Schema for renaming a summary."""
    custom_name: str = Field(..., description="New custom name for the summary", min_length=1, max_length=200)


class SummaryResponse(BaseModel):
    """Schema for summary response."""
    id: str
    recording_id: str
    transcription_id: str
    summary_text: str
    key_points: Optional[List[str]]
    action_items: Optional[List[str]]
    category: Optional[str]
    format: SummaryFormat
    custom_name: Optional[str]
    is_saved: bool
    model_used: str
    created_at: datetime

    class Config:
        from_attributes = True
