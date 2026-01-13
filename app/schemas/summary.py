"""
Pydantic schemas for Summary endpoints.
Request and response models for API validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class SummaryGenerate(BaseModel):
    """Schema for generating a summary."""
    recording_id: str = Field(..., description="ID of the recording to summarize")
    custom_prompt: Optional[str] = Field(None, description="Custom instructions for summary generation")


class SummaryResponse(BaseModel):
    """Schema for summary response."""
    id: str
    recording_id: str
    transcription_id: str
    summary_text: str
    key_points: Optional[List[str]]
    action_items: Optional[List[str]]
    category: Optional[str]
    model_used: str
    created_at: datetime

    class Config:
        from_attributes = True
