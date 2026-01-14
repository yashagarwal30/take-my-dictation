"""
Trial usage limit checking and enforcement.
"""
from fastapi import HTTPException, status
from app.models.user import User, SubscriptionTier

TRIAL_MINUTES_LIMIT = 10.0  # 10 minutes free trial


def check_trial_limits(user: User, duration_minutes: float = 0) -> None:
    """
    Check if a trial user has exceeded their usage limits.
    Raises HTTPException if limits are exceeded.

    Args:
        user: The user to check
        duration_minutes: Optional duration to check against (for pre-upload validation)

    Raises:
        HTTPException: If trial limits are exceeded
    """
    if not user.is_trial_user:
        # Not a trial user, no limits to check
        return

    # Check if trial is already exhausted
    if user.trial_minutes_used >= TRIAL_MINUTES_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "trial_limit_exceeded",
                "message": f"You've used your free {TRIAL_MINUTES_LIMIT} minutes. Subscribe to continue with unlimited recording!",
                "trial_minutes_used": user.trial_minutes_used,
                "trial_limit": TRIAL_MINUTES_LIMIT,
                "upgrade_url": "/subscribe"
            }
        )

    # Check if adding this recording would exceed the limit
    if duration_minutes > 0:
        projected_usage = user.trial_minutes_used + duration_minutes
        if projected_usage > TRIAL_MINUTES_LIMIT:
            remaining = TRIAL_MINUTES_LIMIT - user.trial_minutes_used
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "trial_limit_would_exceed",
                    "message": f"This recording would exceed your free trial limit. You have {remaining:.1f} minutes remaining. Subscribe for unlimited recording!",
                    "trial_minutes_used": user.trial_minutes_used,
                    "trial_minutes_remaining": remaining,
                    "trial_limit": TRIAL_MINUTES_LIMIT,
                    "recording_duration": duration_minutes,
                    "upgrade_url": "/subscribe"
                }
            )


def check_usage_limits(user: User, duration_minutes: float = 0) -> dict:
    """
    Check usage limits for both trial users and paid subscribers.
    Returns usage information and warnings.

    Args:
        user: The user to check
        duration_minutes: Duration in minutes to check against

    Returns:
        dict: Usage information and any warnings

    Raises:
        HTTPException: If limits are exceeded
    """
    # Trial user checks
    if user.is_trial_user:
        check_trial_limits(user, duration_minutes)
        remaining = TRIAL_MINUTES_LIMIT - user.trial_minutes_used
        return {
            "user_type": "trial",
            "trial_minutes_used": user.trial_minutes_used,
            "trial_minutes_remaining": remaining,
            "trial_limit": TRIAL_MINUTES_LIMIT,
            "warning": f"Trial: {remaining:.1f} minutes remaining" if remaining < 2.0 else None
        }

    # Paid subscriber checks
    if user.subscription_tier in [SubscriptionTier.BASIC, SubscriptionTier.PRO]:
        if user.monthly_hours_limit is None:
            # No limit set (shouldn't happen, but handle gracefully)
            return {"user_type": "paid", "unlimited": True}

        hours_used = user.monthly_hours_used or 0.0
        hours_limit = user.monthly_hours_limit

        # Check if limit exceeded
        if hours_used >= hours_limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "monthly_limit_exceeded",
                    "message": f"You've reached your monthly limit of {hours_limit} hours. Resets on {user.usage_reset_at.strftime('%B %d')}.",
                    "hours_used": hours_used,
                    "hours_limit": hours_limit,
                    "reset_date": user.usage_reset_at.isoformat() if user.usage_reset_at else None,
                    "upgrade_url": "/subscribe" if user.subscription_tier == SubscriptionTier.BASIC else None
                }
            )

        # Check if adding this recording would exceed
        if duration_minutes > 0:
            duration_hours = duration_minutes / 60.0
            projected_usage = hours_used + duration_hours
            if projected_usage > hours_limit:
                remaining_hours = hours_limit - hours_used
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "monthly_limit_would_exceed",
                        "message": f"This recording would exceed your monthly limit. You have {remaining_hours:.1f} hours remaining.",
                        "hours_used": hours_used,
                        "hours_remaining": remaining_hours,
                        "hours_limit": hours_limit,
                        "recording_duration_hours": duration_hours,
                        "upgrade_url": "/subscribe" if user.subscription_tier == SubscriptionTier.BASIC else None
                    }
                )

        # Return usage info with warnings
        hours_remaining = hours_limit - hours_used
        usage_percentage = (hours_used / hours_limit) * 100

        warning = None
        if usage_percentage >= 90:
            warning = f"Warning: {usage_percentage:.0f}% of monthly limit used"
        elif hours_remaining < 1.0:
            warning = f"Less than 1 hour remaining this month"

        return {
            "user_type": "paid",
            "subscription_tier": user.subscription_tier.value,
            "hours_used": hours_used,
            "hours_remaining": hours_remaining,
            "hours_limit": hours_limit,
            "usage_percentage": usage_percentage,
            "reset_date": user.usage_reset_at.isoformat() if user.usage_reset_at else None,
            "warning": warning
        }

    # Free tier users (no trial, no subscription)
    return {"user_type": "free", "message": "Subscribe to start recording"}
