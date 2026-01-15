"""
Admin API endpoints.
Comprehensive admin dashboard with user management, analytics, and support tools.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.database import get_db, get_async_session
from app.models.recording import Recording
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.models.user import User, SubscriptionTier
from app.core.config import settings
# from app.core.dependencies import require_admin  # TODO: Implement require_admin
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        API health status
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Get API usage statistics.

    Args:
        db: Database session

    Returns:
        Usage statistics
    """
    # Count recordings
    recordings_count = await db.scalar(
        select(func.count()).select_from(Recording)
    )

    # Count transcriptions
    transcriptions_count = await db.scalar(
        select(func.count()).select_from(Transcription)
    )

    # Count summaries
    summaries_count = await db.scalar(
        select(func.count()).select_from(Summary)
    )

    # Get total storage size
    total_size_result = await db.execute(
        select(func.sum(Recording.file_size))
    )
    total_size = total_size_result.scalar() or 0

    # Get total duration
    total_duration_result = await db.execute(
        select(func.sum(Recording.duration))
    )
    total_duration = total_duration_result.scalar() or 0

    return {
        "recordings": {
            "total": recordings_count or 0,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_duration_seconds": round(total_duration, 2),
            "total_duration_minutes": round(total_duration / 60, 2)
        },
        "transcriptions": {
            "total": transcriptions_count or 0
        },
        "summaries": {
            "total": summaries_count or 0
        }
    }


# Pydantic models for admin operations
class UserLimitUpdate(BaseModel):
    """Model for updating user limits."""
    monthly_hours_limit: Optional[float] = None
    monthly_hours_used: Optional[float] = None


@router.get("/dashboard")
async def get_admin_dashboard(
    db: AsyncSession = Depends(get_async_session)
    # _admin: dict = Depends(require_admin)  # TODO: Add admin authentication
):
    """
    Get comprehensive admin dashboard data.
    Includes user stats, trial conversion, usage metrics, and recent activity.

    Admin-only endpoint.

    Returns:
        Complete dashboard data
    """
    analytics = AnalyticsService()

    # Get comprehensive analytics
    analytics_data = await analytics.get_comprehensive_analytics(db)

    # Get user counts by tier
    user_stats_by_tier = await db.execute(
        select(
            User.subscription_tier,
            func.count(User.id).label('count')
        ).filter(
            User.is_trial_user == False
        ).group_by(User.subscription_tier)
    )

    tier_breakdown = {}
    for row in user_stats_by_tier:
        tier = row.subscription_tier.value if row.subscription_tier else "unknown"
        tier_breakdown[tier] = row.count

    # Get recent users (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_users_result = await db.execute(
        select(func.count(User.id)).filter(
            User.created_at >= week_ago,
            User.is_trial_user == False
        )
    )
    recent_paid_signups = recent_users_result.scalar() or 0

    recent_trials_result = await db.execute(
        select(func.count(User.id)).filter(
            User.created_at >= week_ago,
            User.is_trial_user == True
        )
    )
    recent_trial_starts = recent_trials_result.scalar() or 0

    return {
        "generated_at": datetime.utcnow(),
        "user_stats": {
            "tier_breakdown": tier_breakdown,
            "recent_paid_signups": recent_paid_signups,
            "recent_trial_starts": recent_trial_starts
        },
        "analytics": analytics_data,
        "system": {
            "version": settings.VERSION,
            "project_name": settings.PROJECT_NAME
        }
    }


@router.get("/users")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tier: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
    # _admin: dict = Depends(require_admin)  # TODO: Add admin authentication
):
    """
    Get paginated list of all users with tier and usage information.

    Admin-only endpoint.

    Args:
        skip: Number of users to skip (pagination)
        limit: Maximum number of users to return
        tier: Filter by subscription tier (FREE, BASIC, PRO, TRIAL)
        search: Search by email

    Returns:
        List of users with detailed information
    """
    # Build query
    query = select(User)

    # Apply filters
    if tier:
        if tier.upper() == "TRIAL":
            query = query.filter(User.is_trial_user == True)
        else:
            try:
                tier_enum = SubscriptionTier(tier.upper())
                query = query.filter(
                    User.subscription_tier == tier_enum,
                    User.is_trial_user == False
                )
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")

    if search:
        query = query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.trial_email.ilike(f"%{search}%")
            )
        )

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Format response
    user_list = []
    for user in users:
        user_data = {
            "id": user.id,
            "email": user.email or user.trial_email,
            "is_trial_user": user.is_trial_user,
            "subscription_tier": user.subscription_tier.value if user.subscription_tier else None,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }

        if user.is_trial_user:
            user_data["trial_minutes_used"] = user.trial_minutes_used
            user_data["trial_minutes_remaining"] = max(0, 10.0 - user.trial_minutes_used)
        else:
            user_data["monthly_hours_used"] = user.monthly_hours_used
            user_data["monthly_hours_limit"] = user.monthly_hours_limit
            user_data["monthly_hours_remaining"] = max(0, (user.monthly_hours_limit or 0) - user.monthly_hours_used)
            user_data["usage_percentage"] = round((user.monthly_hours_used / user.monthly_hours_limit * 100), 2) if user.monthly_hours_limit else 0
            user_data["subscription_anniversary_date"] = user.subscription_anniversary_date
            user_data["usage_reset_at"] = user.usage_reset_at

        user_list.append(user_data)

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "users": user_list
    }


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    db: AsyncSession = Depends(get_async_session)
    # _admin: dict = Depends(require_admin)  # TODO: Add admin authentication
):
    """
    Get detailed information about a specific user.

    Admin-only endpoint.

    Args:
        user_id: User ID

    Returns:
        Detailed user information including usage history
    """
    # Get user
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's recordings count
    recordings_result = await db.execute(
        select(func.count(Recording.id)).filter(Recording.user_id == user_id)
    )
    recordings_count = recordings_result.scalar() or 0

    # Get user's summaries count
    summaries_result = await db.execute(
        select(func.count(Summary.id)).join(Recording).filter(Recording.user_id == user_id)
    )
    summaries_count = summaries_result.scalar() or 0

    user_data = {
        "id": user.id,
        "email": user.email or user.trial_email,
        "is_trial_user": user.is_trial_user,
        "subscription_tier": user.subscription_tier.value if user.subscription_tier else None,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "recordings_count": recordings_count,
        "summaries_count": summaries_count
    }

    if user.is_trial_user:
        user_data["trial_info"] = {
            "trial_email": user.trial_email,
            "trial_minutes_used": user.trial_minutes_used,
            "trial_minutes_limit": 10.0,
            "trial_minutes_remaining": max(0, 10.0 - user.trial_minutes_used),
            "usage_percentage": round((user.trial_minutes_used / 10.0 * 100), 2)
        }
    else:
        user_data["subscription_info"] = {
            "tier": user.subscription_tier.value if user.subscription_tier else None,
            "monthly_hours_used": user.monthly_hours_used,
            "monthly_hours_limit": user.monthly_hours_limit,
            "monthly_hours_remaining": max(0, (user.monthly_hours_limit or 0) - user.monthly_hours_used),
            "usage_percentage": round((user.monthly_hours_used / user.monthly_hours_limit * 100), 2) if user.monthly_hours_limit else 0,
            "subscription_anniversary_date": user.subscription_anniversary_date,
            "usage_reset_at": user.usage_reset_at
        }

    return user_data


@router.put("/users/{user_id}/limits")
async def update_user_limits(
    user_id: str,
    limits: UserLimitUpdate,
    db: AsyncSession = Depends(get_async_session)
    # _admin: dict = Depends(require_admin)  # TODO: Add admin authentication
):
    """
    Manually adjust user limits for support purposes.

    Admin-only endpoint.

    Args:
        user_id: User ID
        limits: Updated limit values

    Returns:
        Updated user information
    """
    # Get user
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_trial_user:
        raise HTTPException(
            status_code=400,
            detail="Cannot adjust limits for trial users. Convert to paid first."
        )

    # Update limits
    if limits.monthly_hours_limit is not None:
        user.monthly_hours_limit = limits.monthly_hours_limit

    if limits.monthly_hours_used is not None:
        user.monthly_hours_used = limits.monthly_hours_used

    await db.commit()
    await db.refresh(user)

    return {
        "success": True,
        "user_id": user_id,
        "updated_limits": {
            "monthly_hours_limit": user.monthly_hours_limit,
            "monthly_hours_used": user.monthly_hours_used,
            "monthly_hours_remaining": max(0, (user.monthly_hours_limit or 0) - user.monthly_hours_used)
        },
        "message": "User limits updated successfully"
    }
