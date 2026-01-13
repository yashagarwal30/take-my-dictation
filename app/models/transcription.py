"""
Transcription database model.
Stores transcription text and metadata.
"""
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.database import Base


class Transcription(Base):
    """Transcription model for storing speech-to-text results."""

    __tablename__ = "transcriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recording_id = Column(String, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    text = Column(Text, nullable=False)
    language = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    provider = Column(String, nullable=False)  # whisper, assemblyai, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    recording = relationship("Recording", back_populates="transcription")
    summary = relationship("Summary", back_populates="transcription", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transcription for Recording {self.recording_id}>"
