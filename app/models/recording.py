"""
Recording database model.
Stores metadata about uploaded audio recordings.
"""
from sqlalchemy import Column, String, BigInteger, Float, DateTime, Enum
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
    filename = Column(String, nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    duration = Column(Float, nullable=True)  # in seconds
    format = Column(String, nullable=False)
    status = Column(Enum(RecordingStatus), default=RecordingStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    transcription = relationship("Transcription", back_populates="recording", uselist=False, cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="recording", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Recording {self.filename}>"
