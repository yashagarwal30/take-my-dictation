"""
Usage tracking service for monitoring and enforcing subscription limits.
Handles monthly usage tracking, limit enforcement, and reset logic.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.models.user import User, SubscriptionTier
from app.models.recording import Recording


class UsageTrackingService:
    """Service for tracking and managing user recording usage."""

    @staticmethod
    async def track_recording_usage(
        user_id: str,
        recording_duration_seconds: float,
        db: AsyncSession
    ) -> Dict:
        """
        Track recording usage for a user and update monthly hours used.

        Args:
            user_id: User ID
            recording_duration_seconds: Duration of recording in seconds
            db: Database session

        Returns:
            Dictionary with usage information

        Raises:
            Exception: If user not found
        """
        # Get user
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise Exception(f"User {user_id} not found")

        # Convert seconds to hours
        duration_hours = recording_duration_seconds / 3600.0

        # Update usage based on user type
        if user.is_trial_user:
            # Trial users track in minutes
            duration_minutes = recording_duration_seconds / 60.0
            user.trial_minutes_used += duration_minutes

            return {
                "success": True,
                "user_type": "trial",
                "trial_minutes_used": user.trial_minutes_used,
                "trial_minutes_remaining": max(0, 10.0 - user.trial_minutes_used),
                "duration_tracked_minutes": duration_minutes
            }
        else:
            # Paid users track in hours (monthly)
            user.monthly_hours_used += duration_hours

            # Calculate remaining hours
            hours_limit = user.monthly_hours_limit or 0
            hours_remaining = max(0, hours_limit - user.monthly_hours_used)

            # Calculate usage percentage
            usage_percentage = (user.monthly_hours_used / hours_limit * 100) if hours_limit > 0 else 0

            await db.commit()
            await db.refresh(user)

            return {
                "success": True,
                "user_type": "paid",
                "subscription_tier": user.subscription_tier.value,
                "monthly_hours_used": user.monthly_hours_used,
                "monthly_hours_limit": hours_limit,
                "monthly_hours_remaining": hours_remaining,
                "usage_percentage": usage_percentage,
                "duration_tracked_hours": duration_hours,
                "reset_date": user.usage_reset_at
            }

    @staticmethod
    async def check_usage_limit(
        user_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Check if user has exceeded their usage limit.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dictionary with limit check results
        """
        # Get user
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise Exception(f"User {user_id} not found")

        # Check trial users
        if user.is_trial_user:
            minutes_used = user.trial_minutes_used
            minutes_remaining = max(0, 10.0 - minutes_used)
            limit_exceeded = minutes_used >= 10.0

            return {
                "limit_exceeded": limit_exceeded,
                "user_type": "trial",
                "trial_minutes_used": minutes_used,
                "trial_minutes_remaining": minutes_remaining,
                "usage_percentage": (minutes_used / 10.0 * 100)
            }

        # Check paid users
        hours_limit = user.monthly_hours_limit or 0
        hours_used = user.monthly_hours_used
        hours_remaining = max(0, hours_limit - hours_used)
        limit_exceeded = hours_used >= hours_limit if hours_limit > 0 else False
        usage_percentage = (hours_used / hours_limit * 100) if hours_limit > 0 else 0

        return {
            "limit_exceeded": limit_exceeded,
            "user_type": "paid",
            "subscription_tier": user.subscription_tier.value,
            "monthly_hours_used": hours_used,
            "monthly_hours_limit": hours_limit,
            "monthly_hours_remaining": hours_remaining,
            "usage_percentage": usage_percentage,
            "reset_date": user.usage_reset_at,
            "warning_80_percent": usage_percentage >= 80 and usage_percentage < 100,
            "warning_100_percent": usage_percentage >= 100
        }

    @staticmethod
    async def get_usage_warning_message(usage_info: Dict) -> Optional[str]:
        """
        Generate appropriate warning message based on usage.

        Args:
            usage_info: Usage information from check_usage_limit

        Returns:
            Warning message or None
        """
        if usage_info["user_type"] == "trial":
            if usage_info["limit_exceeded"]:
                return "You've used your free 10 minutes. Subscribe for unlimited recording."
            elif usage_info["usage_percentage"] >= 80:
                minutes_remaining = usage_info["trial_minutes_remaining"]
                return f"Trial warning: {minutes_remaining:.1f} minutes remaining of your free 10 minutes."
            return None

        # Paid users
        if usage_info.get("warning_100_percent"):
            reset_date = usage_info.get("reset_date")
            if reset_date:
                reset_str = reset_date.strftime("%B %d, %Y")
                return f"Monthly limit reached. Resets on {reset_str}."
            return "Monthly limit reached."

        elif usage_info.get("warning_80_percent"):
            hours_used = usage_info["monthly_hours_used"]
            hours_limit = usage_info["monthly_hours_limit"]
            hours_remaining = usage_info["monthly_hours_remaining"]
            return f"Usage warning: {hours_used:.1f} of {hours_limit} hours used. {hours_remaining:.1f} hours remaining."

        return None

    @staticmethod
    async def reset_monthly_usage(
        user_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Reset monthly usage for a user (called on subscription anniversary).

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dictionary with reset information
        """
        # Get user
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise Exception(f"User {user_id} not found")

        # Don't reset trial users
        if user.is_trial_user:
            return {
                "success": False,
                "message": "Trial users don't have monthly resets"
            }

        # Store old usage for logging
        old_usage = user.monthly_hours_used

        # Reset usage
        user.monthly_hours_used = 0.0

        # Calculate next reset date (add 1 month)
        if user.usage_reset_at:
            # Add 1 month to current reset date
            current_reset = user.usage_reset_at
            if current_reset.month == 12:
                next_reset = current_reset.replace(year=current_reset.year + 1, month=1)
            else:
                next_reset = current_reset.replace(month=current_reset.month + 1)
            user.usage_reset_at = next_reset
        else:
            # Set next reset to 1 month from now
            user.usage_reset_at = datetime.utcnow() + timedelta(days=30)

        await db.commit()
        await db.refresh(user)

        return {
            "success": True,
            "user_id": user_id,
            "email": user.email,
            "old_usage_hours": old_usage,
            "new_usage_hours": user.monthly_hours_used,
            "next_reset_date": user.usage_reset_at,
            "monthly_hours_limit": user.monthly_hours_limit
        }

    @staticmethod
    async def get_usage_history(
        user_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Get current usage information for a user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dictionary with current usage stats
        """
        # Get user
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise Exception(f"User {user_id} not found")

        # Trial users
        if user.is_trial_user:
            return {
                "user_type": "trial",
                "trial_minutes_used": user.trial_minutes_used,
                "trial_minutes_limit": 10.0,
                "trial_minutes_remaining": max(0, 10.0 - user.trial_minutes_used),
                "usage_percentage": (user.trial_minutes_used / 10.0 * 100)
            }

        # Paid users
        hours_limit = user.monthly_hours_limit or 0
        hours_used = user.monthly_hours_used
        hours_remaining = max(0, hours_limit - hours_used)
        usage_percentage = (hours_used / hours_limit * 100) if hours_limit > 0 else 0

        return {
            "user_type": "paid",
            "subscription_tier": user.subscription_tier.value,
            "monthly_hours_used": hours_used,
            "monthly_hours_limit": hours_limit,
            "monthly_hours_remaining": hours_remaining,
            "usage_percentage": usage_percentage,
            "reset_date": user.usage_reset_at,
            "subscription_anniversary_date": user.subscription_anniversary_date
        }
