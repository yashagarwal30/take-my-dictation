"""
User schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import SubscriptionTier


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    is_active: bool
    is_verified: bool
    subscription_tier: SubscriptionTier
    monthly_hours_limit: Optional[float] = None
    monthly_hours_used: Optional[float] = None
    subscription_expires_at: Optional[datetime] = None
    razorpay_subscription_id: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Schema for JWT token data."""
    user_id: Optional[str] = None
    email: Optional[str] = None


class SendVerificationCode(BaseModel):
    """Schema for sending verification code."""
    email: EmailStr


class VerifyEmailCode(BaseModel):
    """Schema for verifying email code."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$', description="6-digit verification code")


class VerificationResponse(BaseModel):
    """Schema for verification response."""
    success: bool
    message: str
    expires_in_seconds: Optional[int] = None
