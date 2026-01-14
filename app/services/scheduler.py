"""
Background job scheduler for periodic tasks.
Handles monthly usage resets and other scheduled jobs.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date
from typing import List
import logging

from app.db.database import get_async_session
from app.models.user import User
from app.services.usage_tracking_service import UsageTrackingService
from app.services.audio_retention_service import AudioRetentionService

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """Scheduler for background jobs."""

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.usage_service = UsageTrackingService()
        self.retention_service = AudioRetentionService()

    async def reset_monthly_usage_job(self):
        """
        Background job to reset monthly usage for users on their subscription anniversary.
        Runs daily at midnight UTC to check for users who need reset.
        """
        logger.info("🔄 Starting monthly usage reset job...")

        try:
            # Get database session
            async for db in get_async_session():
                today = date.today()
                current_day = today.day

                # Find users whose subscription anniversary is today
                # and who are not trial users
                result = await db.execute(
                    select(User).filter(
                        User.subscription_anniversary_date == current_day,
                        User.is_trial_user == False
                    )
                )
                users_to_reset = result.scalars().all()

                logger.info(f"📊 Found {len(users_to_reset)} users to reset")

                reset_count = 0
                for user in users_to_reset:
                    try:
                        reset_result = await self.usage_service.reset_monthly_usage(
                            user.id,
                            db
                        )

                        if reset_result["success"]:
                            logger.info(
                                f"✅ Reset usage for {user.email}: "
                                f"{reset_result['old_usage_hours']:.2f}h → 0h"
                            )
                            reset_count += 1
                        else:
                            logger.warning(
                                f"⚠️  Skipped reset for {user.email}: {reset_result.get('message')}"
                            )

                    except Exception as user_error:
                        logger.error(
                            f"❌ Failed to reset usage for {user.email}: {user_error}"
                        )
                        continue

                logger.info(f"✅ Monthly usage reset complete: {reset_count}/{len(users_to_reset)} users reset")

                # Break after first session (we only need one)
                break

        except Exception as e:
            logger.error(f"❌ Monthly usage reset job failed: {e}")

    async def cleanup_expired_audio_job(self):
        """
        Background job to delete expired audio files.
        Runs weekly on Sundays at 2 AM UTC.
        """
        logger.info("🗑️  Starting audio cleanup job...")

        try:
            # Get database session
            async for db in get_async_session():
                cleanup_result = await self.retention_service.cleanup_expired_audio(db)

                logger.info(
                    f"✅ Audio cleanup complete: {cleanup_result['deleted_count']} files deleted, "
                    f"{cleanup_result['failed_count']} failed, "
                    f"{cleanup_result['total_size_freed_mb']} MB freed"
                )

                # Break after first session (we only need one)
                break

        except Exception as e:
            logger.error(f"❌ Audio cleanup job failed: {e}")

    def start(self):
        """Start the scheduler with all jobs."""
        logger.info("🚀 Starting background scheduler...")

        # Add monthly usage reset job (runs daily at midnight UTC)
        self.scheduler.add_job(
            self.reset_monthly_usage_job,
            trigger=CronTrigger(hour=0, minute=0),  # Daily at midnight UTC
            id="monthly_usage_reset",
            name="Monthly Usage Reset",
            replace_existing=True
        )

        logger.info("📅 Scheduled job: Monthly usage reset (daily at midnight UTC)")

        # Add audio cleanup job (runs weekly on Sundays at 2 AM UTC)
        self.scheduler.add_job(
            self.cleanup_expired_audio_job,
            trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),  # Weekly on Sunday at 2 AM UTC
            id="audio_cleanup",
            name="Audio Cleanup",
            replace_existing=True
        )

        logger.info("📅 Scheduled job: Audio cleanup (weekly on Sundays at 2 AM UTC)")

        # Start the scheduler
        self.scheduler.start()
        logger.info("✅ Background scheduler started")

    def shutdown(self):
        """Shutdown the scheduler."""
        logger.info("👋 Shutting down background scheduler...")
        self.scheduler.shutdown()
        logger.info("✅ Background scheduler stopped")


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> BackgroundScheduler:
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackgroundScheduler()
    return _scheduler_instance


async def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler_instance
    if _scheduler_instance is not None:
        _scheduler_instance.shutdown()
        _scheduler_instance = None
