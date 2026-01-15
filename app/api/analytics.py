"""
Analytics API endpoints for tracking and reporting metrics.
Provides insights into trial conversions, usage by tier, and popular formats.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional

from app.db.database import get_async_session
from app.services.analytics_service import AnalyticsService
# from app.core.dependencies import require_admin  # TODO: Implement require_admin

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_analytics_overview(
    db: AsyncSession = Depends(get_async_session),
    # _admin: dict = Depends(require_admin)  # TODO: Add admin authentication
):
    """
    Get comprehensive analytics overview.
    Admin-only endpoint.

    Returns:
        Comprehensive analytics dashboard data including:
        - Total users by type
        - Trial conversion rates
        - Usage by tier
        - Popular summary formats
        - Churn metrics
    """
    analytics = AnalyticsService()
    result = await analytics.get_comprehensive_analytics(db)

    return result


@router.get("/conversions")
async def get_conversion_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_session),
    # _admin: dict = Depends(require_admin)  # TODO: Add admin authentication
):
    """
    Get trial to paid conversion metrics.
    Admin-only endpoint.

    Args:
        days: Number of days to look back (default 30)

    Returns:
        Trial conversion rate and statistics
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    analytics = AnalyticsService()
    result = await analytics.get_trial_conversion_rate(start_date, end_date, db)

    return result


@router.get("/usage-by-tier")
async def get_usage_by_tier(
    db: AsyncSession = Depends(get_async_session),
    # _admin: dict = Depends(require_admin)  # TODO: Add admin authentication
):
    """
    Get usage statistics by subscription tier.
    Admin-only endpoint.

    Returns:
        Usage metrics for each subscription tier including:
        - User count
        - Average hours used
        - Total hours used
    """
    analytics = AnalyticsService()
    result = await analytics.get_usage_by_tier(db)

    return result


@router.get("/popular-formats")
async def get_popular_formats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_session),
    # _admin: dict = Depends(require_admin)  # TODO: Add admin authentication
):
    """
    Get statistics on most popular summary formats.
    Admin-only endpoint.

    Args:
        days: Number of days to look back (default 30)

    Returns:
        Summary format usage statistics with counts and percentages
    """
    analytics = AnalyticsService()
    result = await analytics.get_popular_summary_formats(days, db)

    return result


@router.get("/churn")
async def get_churn_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_session),
    # _admin: dict = Depends(require_admin)  # TODO: Add admin authentication
):
    """
    Get churn rate metrics.
    Admin-only endpoint.

    Args:
        days: Number of days to analyze (default 30)

    Returns:
        Churn rate and related metrics
    """
    analytics = AnalyticsService()
    result = await analytics.get_churn_rate(days, db)

    return result


@router.post("/track/trial-start")
async def track_trial_start(
    trial_email: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Track when a trial is started.
    Internal endpoint called by trial creation flow.

    Args:
        trial_email: Email of trial user

    Returns:
        Tracking confirmation
    """
    analytics = AnalyticsService()
    result = await analytics.track_trial_start(trial_email, db)

    return result


@router.post("/track/conversion")
async def track_trial_conversion(
    user_id: str,
    trial_email: str,
    subscription_tier: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Track when a trial converts to paid.
    Internal endpoint called by conversion flow.

    Args:
        user_id: ID of converted user
        trial_email: Original trial email
        subscription_tier: Subscription tier they chose

    Returns:
        Tracking confirmation
    """
    from app.models.user import SubscriptionTier

    # Validate tier
    try:
        tier = SubscriptionTier(subscription_tier.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")

    analytics = AnalyticsService()
    result = await analytics.track_trial_conversion(user_id, trial_email, tier, db)

    return result
