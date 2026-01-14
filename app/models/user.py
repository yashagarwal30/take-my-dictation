"""
User database model.
Stores user account information and subscription details.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime, date
import uuid
import enum
from app.db.database import Base


class SubscriptionTier(str, enum.Enum):
    """Subscription tier levels."""
    FREE = "free"
    BASIC = "basic"  # $9.99/month, 10 hours/month
    PRO = "pro"      # $19.99/month, 50 hours/month


class User(Base):
    """User model for authentication and subscription management."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)  # Nullable for trial users
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Trial user fields
    is_trial_user = Column(Boolean, default=False, nullable=False, index=True)
    trial_email = Column(String, nullable=True, index=True)  # For tracking trial usage by email
    trial_minutes_used = Column(Float, default=0.0, nullable=False)  # Minutes used in trial

    # Subscription details
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False)
    stripe_customer_id = Column(String, nullable=True, unique=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)

    # Usage tracking
    monthly_hours_limit = Column(Float, nullable=True)  # 10 for Basic, 50 for Pro
    monthly_hours_used = Column(Float, default=0.0, nullable=False)  # Current month usage
    subscription_anniversary_date = Column(Date, nullable=True)  # Day of month for reset
    usage_reset_at = Column(DateTime, nullable=True)  # Next reset timestamp

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    recordings = relationship("Recording", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"
