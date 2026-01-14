"""
Dependencies for FastAPI routes.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User, SubscriptionTier
from app.core.security import decode_access_token
from app.services.usage_tracking_service import UsageTrackingService

# HTTP Bearer token security
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_id: Optional[str] = payload.get("user_id")
    if user_id is None:
        raise credentials_exception

    # Fetch user from database
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get the current user if authenticated, otherwise None."""
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = decode_access_token(token)

        if payload is None:
            return None

        user_id: Optional[str] = payload.get("user_id")
        if user_id is None:
            return None

        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()

        return user if user and user.is_active else None
    except Exception:
        return None


async def check_usage_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Check if user has exceeded their usage limit.

    Raises HTTPException if limit is exceeded.
    Returns user if limit is not exceeded.
    """
    usage_service = UsageTrackingService()
    usage_info = await usage_service.check_usage_limit(current_user.id, db)

    if usage_info["limit_exceeded"]:
        # Generate appropriate error message
        if usage_info["user_type"] == "trial":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Trial limit exceeded",
                    "message": "You've used your free 10 minutes. Subscribe to continue recording.",
                    "trial_minutes_used": usage_info["trial_minutes_used"],
                    "upgrade_required": True
                }
            )
        else:
            # Paid user exceeded monthly limit
            reset_date = usage_info.get("reset_date")
            reset_str = reset_date.strftime("%B %d, %Y") if reset_date else "next month"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Monthly limit exceeded",
                    "message": f"Monthly limit reached. Resets on {reset_str}.",
                    "monthly_hours_used": usage_info["monthly_hours_used"],
                    "monthly_hours_limit": usage_info["monthly_hours_limit"],
                    "reset_date": reset_str,
                    "upgrade_available": usage_info["subscription_tier"] == "basic"
                }
            )

    return current_user


# Feature Gates
# =============================================================================


async def require_basic_or_higher(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require user to have BASIC or PRO subscription tier.

    Blocks trial and free users with upgrade message.

    Usage:
        @router.post("/save-summary")
        async def save_summary(user: User = Depends(require_basic_or_higher)):
            ...
    """
    if current_user.subscription_tier in [SubscriptionTier.FREE, None]:
        # Check if user is trial
        if current_user.is_trial_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Trial users cannot save summaries",
                    "message": "Subscribe to save summaries and get unlimited recording time.",
                    "feature": "save_to_dashboard",
                    "required_tier": "basic",
                    "upgrade_required": True
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Subscription required",
                    "message": "Subscribe to Basic or Pro plan to save summaries to your dashboard.",
                    "feature": "save_to_dashboard",
                    "required_tier": "basic",
                    "upgrade_required": True
                }
            )

    return current_user


async def require_pro(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require user to have PRO subscription tier.

    Blocks trial, free, and basic users with upgrade message.

    Usage:
        @router.post("/enable-audio-retention")
        async def enable_retention(user: User = Depends(require_pro)):
            ...
    """
    if current_user.subscription_tier != SubscriptionTier.PRO:
        # Determine appropriate message
        if current_user.is_trial_user:
            message = "Upgrade to Pro plan for 10-day audio retention and regeneration."
            current_plan = "trial"
        elif current_user.subscription_tier == SubscriptionTier.BASIC:
            message = "Upgrade to Pro plan for 10-day audio retention and regeneration."
            current_plan = "basic"
        else:
            message = "Subscribe to Pro plan for 10-day audio retention and regeneration."
            current_plan = "free"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Pro subscription required",
                "message": message,
                "feature": "audio_retention",
                "required_tier": "pro",
                "current_tier": current_plan,
                "upgrade_required": True
            }
        )

    return current_user


async def require_can_regenerate(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require that user has Pro tier (for audio retention) to regenerate summaries.

    This is used for summary regeneration which requires the audio file to still exist.
    Only Pro users have 10-day audio retention enabled.

    Usage:
        @router.post("/summaries/regenerate")
        async def regenerate(user: User = Depends(require_can_regenerate)):
            ...
    """
    if current_user.subscription_tier != SubscriptionTier.PRO:
        # Determine appropriate message
        if current_user.is_trial_user:
            message = "Regeneration requires Pro plan with audio retention enabled."
            current_plan = "trial"
        elif current_user.subscription_tier == SubscriptionTier.BASIC:
            message = "Regeneration requires Pro plan with audio retention. Upgrade to Pro to regenerate summaries with different formats."
            current_plan = "basic"
        else:
            message = "Regeneration requires Pro plan with audio retention enabled."
            current_plan = "free"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Pro subscription required for regeneration",
                "message": message,
                "feature": "regenerate_summary",
                "required_tier": "pro",
                "current_tier": current_plan,
                "upgrade_required": True,
                "reason": "Audio retention is only available with Pro plan"
            }
        )

    return current_user


async def require_paid_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require user to be a paying customer (not trial user).

    Allows FREE, BASIC, and PRO users, but blocks trial users.

    Usage:
        @router.get("/dashboard")
        async def dashboard(user: User = Depends(require_paid_user)):
            ...
    """
    if current_user.is_trial_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Account registration required",
                "message": "Create an account to access the dashboard and save your work.",
                "feature": "dashboard_access",
                "upgrade_required": True,
                "action": "convert_trial"
            }
        )

    return current_user
