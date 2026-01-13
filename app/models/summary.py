"""
Summary database model.
Stores AI-generated summaries and key points.
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.database import Base


class Summary(Base):
    """Summary model for storing AI-generated summaries."""

    __tablename__ = "summaries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recording_id = Column(String, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    transcription_id = Column(String, ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    summary_text = Column(Text, nullable=False)
    key_points = Column(JSON, nullable=True)  # List of key points
    action_items = Column(JSON, nullable=True)  # List of action items
    category = Column(String, nullable=True)  # meeting_notes, lecture, memo, etc.
    model_used = Column(String, nullable=False)  # claude-3-opus-20240229, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    recording = relationship("Recording", back_populates="summary")
    transcription = relationship("Transcription", back_populates="summary")

    def __repr__(self):
        return f"<Summary for Recording {self.recording_id}>"
