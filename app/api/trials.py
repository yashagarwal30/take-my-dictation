"""
Free trial API endpoints for email-only trial access.
Allows users to try the service with 10 minutes of free transcription.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.db.database import get_db
from app.models.user import User, SubscriptionTier
from app.core.security import create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/trials", tags=["Trials"])

# Trial configuration
TRIAL_MINUTES_LIMIT = 10.0  # 10 minutes free trial
TRIAL_TOKEN_EXPIRE_HOURS = 24  # Trial session expires in 24 hours


class TrialStartRequest(BaseModel):
    """Request schema for starting a trial."""
    email: EmailStr


class TrialStartResponse(BaseModel):
    """Response schema for trial start."""
    access_token: str
    token_type: str = "bearer"
    trial_minutes_remaining: float
    message: str


class TrialUsageResponse(BaseModel):
    """Response schema for trial usage."""
    email: str
    trial_minutes_used: float
    trial_minutes_remaining: float
    trial_limit: float
    is_trial_expired: bool
    upgrade_message: Optional[str] = None


@router.post("/start", response_model=TrialStartResponse, status_code=status.HTTP_201_CREATED)
async def start_trial(
    data: TrialStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a free trial with email-only entry (no password required).
    Creates a temporary trial user with 10 minutes of free transcription.
    """
    email_lower = data.email.lower().strip()

    # Validate email format
    if not email_lower or "@" not in email_lower:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address"
        )

    try:
        # Check if email already used trial
        result = await db.execute(
            select(User).filter(
                User.trial_email == email_lower
            )
        )
        existing_trial = result.scalar_one_or_none()

        if existing_trial:
            # Trial already used by this email
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email has already been used for a free trial. Please subscribe to continue using the service."
            )

        # Check if this is a registered user trying to use trial
        result = await db.execute(
            select(User).filter(User.email == email_lower)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is already registered. Please log in instead."
            )

        # Create new trial user
        trial_user = User(
            email=None,  # Trial users don't have email in the email field
            trial_email=email_lower,  # Track by trial_email
            hashed_password=None,  # No password for trial users
            is_trial_user=True,
            trial_minutes_used=0.0,
            subscription_tier=SubscriptionTier.FREE,
            is_verified=False,  # Trial users are not verified
            is_active=True
        )

        db.add(trial_user)
        await db.commit()
        await db.refresh(trial_user)

        # Create short-lived JWT token for trial session (24 hours)
        access_token = create_access_token(
            data={
                "user_id": trial_user.id,
                "email": email_lower,
                "is_trial": True
            },
            expires_delta=timedelta(hours=TRIAL_TOKEN_EXPIRE_HOURS)
        )

        return TrialStartResponse(
            access_token=access_token,
            trial_minutes_remaining=TRIAL_MINUTES_LIMIT,
            message=f"Welcome! You have {TRIAL_MINUTES_LIMIT} minutes of free transcription. No signup required!"
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"ERROR in start_trial: {type(e).__name__}: {str(e)}")  # Debug logging
        import traceback
        traceback.print_exc()  # Print full traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start trial. Please try again."
        )


@router.get("/usage", response_model=TrialUsageResponse)
async def get_trial_usage(
    current_user: User = Depends(get_current_user)
):
    """
    Get current trial usage and remaining time.
    Only accessible by trial users.
    """
    # Verify this is a trial user
    if not current_user.is_trial_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for trial users"
        )

    minutes_used = current_user.trial_minutes_used
    minutes_remaining = max(0.0, TRIAL_MINUTES_LIMIT - minutes_used)
    is_expired = minutes_used >= TRIAL_MINUTES_LIMIT

    upgrade_message = None
    if is_expired:
        upgrade_message = "Your free trial has ended. Subscribe to continue with unlimited recording!"
    elif minutes_remaining < 2.0:
        upgrade_message = f"Only {minutes_remaining:.1f} minutes left! Subscribe for unlimited recording."

    return TrialUsageResponse(
        email=current_user.trial_email,
        trial_minutes_used=minutes_used,
        trial_minutes_remaining=minutes_remaining,
        trial_limit=TRIAL_MINUTES_LIMIT,
        is_trial_expired=is_expired,
        upgrade_message=upgrade_message
    )


@router.post("/check-eligibility")
async def check_trial_eligibility(
    data: TrialStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Check if an email is eligible for a free trial.
    Does not create a trial, just checks eligibility.
    """
    email_lower = data.email.lower().strip()

    try:
        # Check if email already used trial
        result = await db.execute(
            select(User).filter(User.trial_email == email_lower)
        )
        existing_trial = result.scalar_one_or_none()

        if existing_trial:
            return {
                "eligible": False,
                "reason": "Email already used for trial",
                "message": "This email has already been used for a free trial. Please subscribe to continue."
            }

        # Check if email is registered
        result = await db.execute(
            select(User).filter(User.email == email_lower)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return {
                "eligible": False,
                "reason": "Email already registered",
                "message": "This email is already registered. Please log in instead."
            }

        return {
            "eligible": True,
            "trial_minutes": TRIAL_MINUTES_LIMIT,
            "message": f"Get {TRIAL_MINUTES_LIMIT} minutes of free transcription!"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check trial eligibility"
        )


@router.post("/convert-to-paid")
async def convert_trial_to_paid(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Convert a trial user to a paid account.
    User must complete registration and subscribe.
    This endpoint is for future use when implementing trial conversion flow.
    """
    if not current_user.is_trial_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only trial users can be converted"
        )

    return {
        "message": "To convert your trial to a paid account, please complete registration and choose a subscription plan.",
        "trial_email": current_user.trial_email,
        "trial_minutes_used": current_user.trial_minutes_used
    }
