"""
Email verification model.
Stores verification codes for email verification during signup.
"""
from sqlalchemy import Column, String, DateTime, Boolean
from datetime import datetime, timedelta
import uuid
import random
from app.db.database import Base


class EmailVerification(Base):
    """Email verification code model."""

    __tablename__ = "email_verifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False, index=True)
    code = Column(String(6), nullable=False, index=True)  # 6-digit verification code
    expires_at = Column(DateTime, nullable=False, index=True)  # 15 minutes from creation
    verified_at = Column(DateTime, nullable=True)  # When code was verified
    is_used = Column(Boolean, default=False, nullable=False)  # Prevent code reuse
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def generate_code() -> str:
        """Generate a random 6-digit verification code."""
        return str(random.randint(100000, 999999))

    @classmethod
    def create_verification(cls, email: str) -> "EmailVerification":
        """Create a new verification code for an email."""
        code = cls.generate_code()
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        return cls(
            email=email.lower(),
            code=code,
            expires_at=expires_at
        )

    def is_valid(self) -> bool:
        """Check if verification code is still valid."""
        if self.is_used:
            return False
        if self.verified_at is not None:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True

    def verify(self) -> bool:
        """Mark code as verified."""
        if not self.is_valid():
            return False
        self.verified_at = datetime.utcnow()
        self.is_used = True
        return True

    def __repr__(self):
        return f"<EmailVerification {self.email} - {self.code}>"
