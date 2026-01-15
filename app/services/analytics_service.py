"""
Analytics tracking service for monitoring user behavior and business metrics.
Tracks trial starts, conversions, usage by tier, and popular summary formats.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from app.models.user import User, SubscriptionTier
from app.models.recording import Recording
from app.models.summary import Summary, SummaryFormat

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for tracking and analyzing application metrics."""

    @staticmethod
    async def track_trial_start(
        trial_email: str,
        db: AsyncSession
    ) -> Dict:
        """
        Track when a new trial is started.

        Args:
            trial_email: Email of trial user
            db: Database session

        Returns:
            Dictionary with tracking result
        """
        logger.info(f"📊 Trial started: {trial_email}")

        # Trial start is already tracked in the User model when is_trial_user=True
        # This method can be extended to log to external analytics services

        return {
            "event": "trial_start",
            "email": trial_email,
            "timestamp": datetime.utcnow()
        }

    @staticmethod
    async def track_trial_conversion(
        user_id: str,
        trial_email: str,
        subscription_tier: SubscriptionTier,
        db: AsyncSession
    ) -> Dict:
        """
        Track when a trial user converts to paid.

        Args:
            user_id: Converted user ID
            trial_email: Original trial email
            subscription_tier: Tier they subscribed to
            db: Database session

        Returns:
            Dictionary with tracking result
        """
        logger.info(
            f"💰 Trial conversion: {trial_email} → {subscription_tier.value}"
        )

        return {
            "event": "trial_conversion",
            "user_id": user_id,
            "trial_email": trial_email,
            "tier": subscription_tier.value,
            "timestamp": datetime.utcnow()
        }

    @staticmethod
    async def get_trial_conversion_rate(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: AsyncSession = None
    ) -> Dict:
        """
        Calculate trial to paid conversion rate.

        Args:
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            db: Database session

        Returns:
            Dictionary with conversion metrics
        """
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Count trial users created in range
        trial_result = await db.execute(
            select(func.count(User.id)).filter(
                User.is_trial_user == True,
                User.created_at >= start_date,
                User.created_at <= end_date
            )
        )
        trial_count = trial_result.scalar() or 0

        # Count users who converted (had trial_email but are now paid users)
        # Note: This requires tracking trial_email even after conversion
        conversion_result = await db.execute(
            select(func.count(User.id)).filter(
                User.trial_email.isnot(None),
                User.is_trial_user == False,
                User.subscription_tier.in_([SubscriptionTier.BASIC, SubscriptionTier.PRO]),
                User.created_at >= start_date,
                User.created_at <= end_date
            )
        )
        converted_count = conversion_result.scalar() or 0

        conversion_rate = (converted_count / trial_count * 100) if trial_count > 0 else 0

        logger.info(
            f"📊 Conversion rate ({start_date.date()} to {end_date.date()}): "
            f"{conversion_rate:.2f}% ({converted_count}/{trial_count})"
        )

        return {
            "period_start": start_date,
            "period_end": end_date,
            "trial_starts": trial_count,
            "conversions": converted_count,
            "conversion_rate_percent": round(conversion_rate, 2)
        }

    @staticmethod
    async def get_usage_by_tier(
        db: AsyncSession
    ) -> Dict:
        """
        Get usage statistics broken down by subscription tier.

        Args:
            db: Database session

        Returns:
            Dictionary with usage by tier
        """
        # Get user counts by tier
        tier_result = await db.execute(
            select(
                User.subscription_tier,
                func.count(User.id).label('user_count'),
                func.avg(User.monthly_hours_used).label('avg_hours_used'),
                func.sum(User.monthly_hours_used).label('total_hours_used')
            ).filter(
                User.is_trial_user == False
            ).group_by(User.subscription_tier)
        )

        tier_stats = {}
        for row in tier_result:
            tier = row.subscription_tier.value if row.subscription_tier else "unknown"
            tier_stats[tier] = {
                "user_count": row.user_count,
                "avg_hours_used": round(float(row.avg_hours_used or 0), 2),
                "total_hours_used": round(float(row.total_hours_used or 0), 2)
            }

        # Get trial user stats separately
        trial_result = await db.execute(
            select(
                func.count(User.id).label('user_count'),
                func.avg(User.trial_minutes_used).label('avg_minutes_used'),
                func.sum(User.trial_minutes_used).label('total_minutes_used')
            ).filter(User.is_trial_user == True)
        )

        trial_row = trial_result.first()
        if trial_row and trial_row.user_count > 0:
            tier_stats['trial'] = {
                "user_count": trial_row.user_count,
                "avg_minutes_used": round(float(trial_row.avg_minutes_used or 0), 2),
                "total_minutes_used": round(float(trial_row.total_minutes_used or 0), 2)
            }

        logger.info(f"📊 Usage by tier: {tier_stats}")

        return tier_stats

    @staticmethod
    async def get_popular_summary_formats(
        days: int = 30,
        db: AsyncSession = None
    ) -> Dict:
        """
        Get statistics on most popular summary formats.

        Args:
            days: Number of days to look back
            db: Database session

        Returns:
            Dictionary with format usage statistics
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get format counts
        format_result = await db.execute(
            select(
                Summary.format,
                func.count(Summary.id).label('count')
            ).filter(
                Summary.created_at >= start_date
            ).group_by(Summary.format).order_by(func.count(Summary.id).desc())
        )

        format_stats = []
        total_summaries = 0

        for row in format_result:
            count = row.count
            total_summaries += count
            format_stats.append({
                "format": row.format.value if row.format else "unknown",
                "count": count
            })

        # Calculate percentages
        for stat in format_stats:
            stat['percentage'] = round(stat['count'] / total_summaries * 100, 2) if total_summaries > 0 else 0

        logger.info(f"📊 Popular formats (last {days} days): {format_stats}")

        return {
            "period_days": days,
            "total_summaries": total_summaries,
            "formats": format_stats
        }

    @staticmethod
    async def get_churn_rate(
        days: int = 30,
        db: AsyncSession = None
    ) -> Dict:
        """
        Calculate churn rate (users who downgraded or cancelled).
        Note: This requires tracking subscription cancellations/downgrades.

        Args:
            days: Number of days to analyze
            db: Database session

        Returns:
            Dictionary with churn metrics
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Count active paid users at start of period
        # This is a simplified calculation - in production, you'd track
        # subscription status changes in a separate events table

        active_users_result = await db.execute(
            select(func.count(User.id)).filter(
                User.is_trial_user == False,
                User.subscription_tier.in_([SubscriptionTier.BASIC, SubscriptionTier.PRO]),
                User.created_at <= start_date
            )
        )
        active_users = active_users_result.scalar() or 0

        # Count users who became inactive/downgraded (simplified)
        # In production, track actual cancellation events
        churned_users_result = await db.execute(
            select(func.count(User.id)).filter(
                User.is_trial_user == False,
                User.subscription_tier == SubscriptionTier.FREE,
                User.updated_at >= start_date,
                User.created_at < start_date
            )
        )
        churned_users = churned_users_result.scalar() or 0

        churn_rate = (churned_users / active_users * 100) if active_users > 0 else 0

        logger.info(
            f"📊 Churn rate (last {days} days): "
            f"{churn_rate:.2f}% ({churned_users}/{active_users})"
        )

        return {
            "period_days": days,
            "active_users_start": active_users,
            "churned_users": churned_users,
            "churn_rate_percent": round(churn_rate, 2)
        }

    @staticmethod
    async def get_comprehensive_analytics(
        db: AsyncSession
    ) -> Dict:
        """
        Get comprehensive analytics dashboard data.

        Args:
            db: Database session

        Returns:
            Dictionary with all analytics metrics
        """
        logger.info("📊 Generating comprehensive analytics report...")

        # Get all metrics
        conversion_metrics = await AnalyticsService.get_trial_conversion_rate(db=db)
        usage_by_tier = await AnalyticsService.get_usage_by_tier(db)
        popular_formats = await AnalyticsService.get_popular_summary_formats(db=db)
        churn_metrics = await AnalyticsService.get_churn_rate(db=db)

        # Get total user counts
        total_users_result = await db.execute(
            select(func.count(User.id)).filter(User.is_trial_user == False)
        )
        total_paid_users = total_users_result.scalar() or 0

        trial_users_result = await db.execute(
            select(func.count(User.id)).filter(User.is_trial_user == True)
        )
        total_trial_users = trial_users_result.scalar() or 0

        # Get total recordings
        recordings_result = await db.execute(
            select(func.count(Recording.id))
        )
        total_recordings = recordings_result.scalar() or 0

        # Get total summaries
        summaries_result = await db.execute(
            select(func.count(Summary.id))
        )
        total_summaries = summaries_result.scalar() or 0

        return {
            "generated_at": datetime.utcnow(),
            "overview": {
                "total_paid_users": total_paid_users,
                "total_trial_users": total_trial_users,
                "total_recordings": total_recordings,
                "total_summaries": total_summaries
            },
            "trial_conversion": conversion_metrics,
            "usage_by_tier": usage_by_tier,
            "popular_formats": popular_formats,
            "churn": churn_metrics
        }
