"""
Audio retention service for managing audio file lifecycle.
Handles retention policies, scheduled deletion, and cleanup.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Dict, Optional
import os
import logging

from app.models.user import User, SubscriptionTier
from app.models.recording import Recording

logger = logging.getLogger(__name__)


class AudioRetentionService:
    """Service for managing audio file retention and cleanup."""

    @staticmethod
    async def set_retention_policy(
        recording: Recording,
        user: Optional[User],
        db: AsyncSession
    ) -> Dict:
        """
        Set audio retention policy based on user's subscription tier.

        Args:
            recording: Recording instance
            user: User instance (can be None for anonymous uploads)
            db: Database session

        Returns:
            Dictionary with retention info

        Policy:
        - FREE/BASIC users: Audio deleted immediately after transcription
        - PRO users: Audio retained for 10 days (can regenerate summaries)
        - No user (anonymous): Audio deleted immediately
        """
        now = datetime.utcnow()

        # Default: immediate deletion
        recording.audio_delete_at = now
        recording.can_regenerate = False
        recording.audio_retention_enabled = False

        if user and user.subscription_tier == SubscriptionTier.PRO:
            # Pro users get 10-day retention
            recording.audio_delete_at = now + timedelta(days=10)
            recording.can_regenerate = True
            recording.audio_retention_enabled = True

            await db.commit()
            await db.refresh(recording)

            return {
                "retention_enabled": True,
                "tier": "pro",
                "audio_delete_at": recording.audio_delete_at,
                "days_remaining": 10,
                "can_regenerate": True
            }

        elif user:
            # Free/Basic users: immediate deletion
            tier = user.subscription_tier.value
            await db.commit()
            await db.refresh(recording)

            return {
                "retention_enabled": False,
                "tier": tier,
                "audio_delete_at": recording.audio_delete_at,
                "days_remaining": 0,
                "can_regenerate": False,
                "message": "Upgrade to Pro to enable 10-day audio retention"
            }

        else:
            # Anonymous upload
            await db.commit()
            await db.refresh(recording)

            return {
                "retention_enabled": False,
                "tier": "anonymous",
                "audio_delete_at": recording.audio_delete_at,
                "days_remaining": 0,
                "can_regenerate": False
            }

    @staticmethod
    async def check_retention_status(
        recording_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Check current retention status for a recording.

        Args:
            recording_id: Recording ID
            db: Database session

        Returns:
            Dictionary with retention status
        """
        result = await db.execute(
            select(Recording).filter(Recording.id == recording_id)
        )
        recording = result.scalar_one_or_none()

        if not recording:
            raise Exception(f"Recording {recording_id} not found")

        now = datetime.utcnow()
        audio_exists = os.path.exists(recording.file_path) if recording.file_path else False

        # Calculate days remaining
        days_remaining = 0
        if recording.audio_delete_at and recording.audio_delete_at > now:
            delta = recording.audio_delete_at - now
            days_remaining = delta.days + (1 if delta.seconds > 0 else 0)

        return {
            "recording_id": recording_id,
            "audio_retention_enabled": recording.audio_retention_enabled,
            "audio_delete_at": recording.audio_delete_at,
            "can_regenerate": recording.can_regenerate,
            "audio_exists": audio_exists,
            "days_remaining": days_remaining,
            "scheduled_for_deletion": recording.audio_delete_at <= now if recording.audio_delete_at else False
        }

    @staticmethod
    async def enable_retention(
        recording_id: str,
        user: User,
        db: AsyncSession
    ) -> Dict:
        """
        Enable 10-day audio retention for a recording (Pro users only).

        Args:
            recording_id: Recording ID
            user: User instance
            db: Database session

        Returns:
            Dictionary with updated retention info

        Raises:
            Exception: If user is not Pro or recording not found
        """
        # Check if user is Pro
        if user.subscription_tier != SubscriptionTier.PRO:
            raise Exception("Audio retention is only available for Pro users")

        # Get recording
        result = await db.execute(
            select(Recording).filter(Recording.id == recording_id)
        )
        recording = result.scalar_one_or_none()

        if not recording:
            raise Exception(f"Recording {recording_id} not found")

        # Check ownership
        if recording.user_id != user.id:
            raise Exception("You can only manage retention for your own recordings")

        # Enable retention
        now = datetime.utcnow()
        recording.audio_retention_enabled = True
        recording.audio_delete_at = now + timedelta(days=10)
        recording.can_regenerate = True

        await db.commit()
        await db.refresh(recording)

        return {
            "success": True,
            "recording_id": recording_id,
            "audio_retention_enabled": True,
            "audio_delete_at": recording.audio_delete_at,
            "days_remaining": 10,
            "can_regenerate": True
        }

    @staticmethod
    async def delete_audio_file(
        recording_id: str,
        user: Optional[User],
        db: AsyncSession,
        force: bool = False
    ) -> Dict:
        """
        Manually delete audio file for a recording.

        Args:
            recording_id: Recording ID
            user: User instance (None for system cleanup)
            db: Database session
            force: If True, skip ownership check (for system cleanup)

        Returns:
            Dictionary with deletion result
        """
        # Get recording
        result = await db.execute(
            select(Recording).filter(Recording.id == recording_id)
        )
        recording = result.scalar_one_or_none()

        if not recording:
            raise Exception(f"Recording {recording_id} not found")

        # Check ownership (unless force)
        if not force and user and recording.user_id != user.id:
            raise Exception("You can only delete audio for your own recordings")

        # Delete physical file
        file_deleted = False
        if recording.file_path and os.path.exists(recording.file_path):
            try:
                os.remove(recording.file_path)
                file_deleted = True
            except Exception as e:
                print(f"⚠️  Failed to delete audio file {recording.file_path}: {e}")

        # Update database
        recording.can_regenerate = False
        recording.audio_retention_enabled = False
        recording.audio_delete_at = datetime.utcnow()  # Mark as deleted

        await db.commit()
        await db.refresh(recording)

        return {
            "success": True,
            "recording_id": recording_id,
            "file_deleted": file_deleted,
            "can_regenerate": False,
            "audio_retention_enabled": False
        }

    @staticmethod
    async def cleanup_expired_audio(db: AsyncSession) -> Dict:
        """
        Background job to delete expired audio files.
        Queries recordings where audio_delete_at <= now AND can_regenerate = true.
        Deletes audio file from storage and updates can_regenerate = false.
        Keeps transcription and summary intact.

        Args:
            db: Database session

        Returns:
            Dictionary with cleanup statistics
        """
        now = datetime.utcnow()

        # Find recordings with expired audio that haven't been cleaned up yet
        result = await db.execute(
            select(Recording).filter(
                Recording.audio_delete_at <= now,
                Recording.can_regenerate == True  # Still has audio file
            )
        )
        expired_recordings = result.scalars().all()

        logger.info(f"📊 Found {len(expired_recordings)} expired audio files to clean up")

        deleted_count = 0
        failed_count = 0
        total_size_freed = 0

        for recording in expired_recordings:
            try:
                file_size = recording.file_size if recording.file_size else 0
                file_path = recording.file_path

                # Delete physical file
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    total_size_freed += file_size
                    deleted_count += 1

                    # Calculate how long ago the file was supposed to be deleted
                    overdue_delta = now - recording.audio_delete_at
                    overdue_days = overdue_delta.days
                    overdue_info = f" (overdue by {overdue_days} days)" if overdue_days > 0 else ""

                    logger.info(
                        f"🗑️  Deleted expired audio: {recording.id[:8]}... "
                        f"({round(file_size / (1024 * 1024), 2)} MB){overdue_info}"
                    )
                else:
                    # File already deleted or doesn't exist
                    logger.warning(
                        f"⚠️  Audio file not found for recording {recording.id[:8]}..., "
                        f"updating database only"
                    )

                # Update database - keep transcription and summary, just mark audio as deleted
                recording.can_regenerate = False
                recording.audio_retention_enabled = False

            except Exception as e:
                logger.error(f"❌ Failed to delete audio for recording {recording.id[:8]}...: {e}")
                failed_count += 1
                continue

        # Commit all changes
        if deleted_count > 0 or failed_count > 0:
            await db.commit()
            logger.info(f"💾 Committed {deleted_count + failed_count} database updates")

        # Log final summary
        if deleted_count > 0:
            logger.info(
                f"✅ Audio cleanup successful: {deleted_count} files deleted, "
                f"{round(total_size_freed / (1024 * 1024), 2)} MB freed"
            )
        if failed_count > 0:
            logger.warning(f"⚠️  {failed_count} files failed to delete")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "total_size_freed_bytes": total_size_freed,
            "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2)
        }
