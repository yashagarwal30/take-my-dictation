"""
Recording database model.
Stores metadata about uploaded audio recordings.
"""
from sqlalchemy import Column, String, BigInteger, Float, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.database import Base


class RecordingStatus(str, enum.Enum):
    """Status of a recording."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Recording(Base):
    """Recording model for storing audio file metadata."""

    __tablename__ = "recordings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # Nullable for trial users
    filename = Column(String, nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    custom_name = Column(String, nullable=True)  # User-provided name for saved recordings
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    duration = Column(Float, nullable=True)  # in seconds
    format = Column(String, nullable=False)
    status = Column(Enum(RecordingStatus), default=RecordingStatus.PENDING, nullable=False)

    # Audio retention fields (Pro users)
    audio_retention_enabled = Column(Boolean, default=False, nullable=False)  # Pro user choice
    audio_delete_at = Column(DateTime, nullable=True, index=True)  # Scheduled deletion timestamp
    can_regenerate = Column(Boolean, default=False, nullable=False)  # If audio still available for regeneration

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="recordings")
    transcription = relationship("Transcription", back_populates="recording", uselist=False, cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="recording", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Recording {self.filename}>"
