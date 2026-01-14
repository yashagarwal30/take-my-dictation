"""
User API endpoints.
Handles user profile, usage tracking, and account management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict

from app.db.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.usage_tracking_service import UsageTrackingService

router = APIRouter()


@router.get("/usage", response_model=Dict)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current usage information for the authenticated user.

    Returns:
        Usage statistics including hours used, limit, remaining, and reset date

    Example response for paid users:
    {
        "user_type": "paid",
        "subscription_tier": "basic",
        "monthly_hours_used": 5.5,
        "monthly_hours_limit": 10.0,
        "monthly_hours_remaining": 4.5,
        "usage_percentage": 55.0,
        "reset_date": "2026-02-15T00:00:00",
        "subscription_anniversary_date": 15
    }

    Example response for trial users:
    {
        "user_type": "trial",
        "trial_minutes_used": 7.5,
        "trial_minutes_limit": 10.0,
        "trial_minutes_remaining": 2.5,
        "usage_percentage": 75.0
    }
    """
    usage_service = UsageTrackingService()
    usage_info = await usage_service.get_usage_history(current_user.id, db)

    # Add warning messages if applicable
    check_info = await usage_service.check_usage_limit(current_user.id, db)
    warning = await usage_service.get_usage_warning_message(check_info)

    if warning:
        usage_info["warning"] = warning
        usage_info["warning_level"] = "critical" if check_info.get("warning_100_percent") else "warning"

    return usage_info


@router.get("/usage/check", response_model=Dict)
async def check_usage_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if user can upload more recordings (usage limit check).

    Returns:
        Detailed limit check with warnings

    Example response:
    {
        "limit_exceeded": false,
        "user_type": "paid",
        "subscription_tier": "basic",
        "monthly_hours_used": 8.0,
        "monthly_hours_limit": 10.0,
        "monthly_hours_remaining": 2.0,
        "usage_percentage": 80.0,
        "reset_date": "2026-02-15T00:00:00",
        "warning_80_percent": true,
        "warning_100_percent": false,
        "can_upload": true
    }
    """
    usage_service = UsageTrackingService()
    usage_info = await usage_service.check_usage_limit(current_user.id, db)

    # Add can_upload flag
    usage_info["can_upload"] = not usage_info["limit_exceeded"]

    # Add warning message
    warning = await usage_service.get_usage_warning_message(usage_info)
    if warning:
        usage_info["warning_message"] = warning

    return usage_info


@router.get("/me", response_model=Dict)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile information.

    Returns:
        User profile data
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_trial_user": current_user.is_trial_user,
        "subscription_tier": current_user.subscription_tier.value,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at
    }
