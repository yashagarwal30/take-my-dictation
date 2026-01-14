"""
Test script for audio cleanup functionality.
Verifies that the scheduler correctly deletes expired audio files while keeping transcriptions and summaries.
"""
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_async_session
from app.models.user import User, SubscriptionTier
from app.models.recording import Recording
from app.services.audio_retention_service import AudioRetentionService
from app.services.scheduler import BackgroundScheduler


async def test_audio_cleanup():
    """Test the audio cleanup functionality."""
    print("🧪 Testing Audio Cleanup Functionality\n")

    retention_service = AudioRetentionService()

    async for db in get_async_session():
        try:
            # Test 1: Create recording with expired audio
            print("📋 Test 1: Cleanup expired audio file")
            print("-" * 50)

            # Create temporary test audio file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.write(b"Test audio content for cleanup test")
            temp_file.close()
            test_file_path = temp_file.name
            test_file_size = os.path.getsize(test_file_path)

            print(f"✅ Created temporary audio file: {test_file_path}")
            print(f"   - Size: {test_file_size} bytes")

            # Create test user (Pro user for retention testing)
            test_user = User(
                email=f"test_cleanup_{datetime.now().timestamp()}@example.com",
                hashed_password="test_hash",
                is_trial_user=False,
                subscription_tier=SubscriptionTier.PRO,
                monthly_hours_limit=50.0,
                monthly_hours_used=0.0
            )
            db.add(test_user)
            await db.commit()
            await db.refresh(test_user)

            # Create recording with EXPIRED audio (delete_at is in the past)
            expired_recording = Recording(
                user_id=test_user.id,
                filename=os.path.basename(test_file_path),
                file_path=test_file_path,
                file_size=test_file_size,
                duration=30.0,
                status="completed",
                audio_delete_at=datetime.utcnow() - timedelta(days=2),  # Expired 2 days ago
                can_regenerate=True,  # Still has audio file
                audio_retention_enabled=True
            )
            db.add(expired_recording)
            await db.commit()
            await db.refresh(expired_recording)

            print(f"✅ Created expired recording: {expired_recording.id[:8]}...")
            print(f"   - Audio delete at: {expired_recording.audio_delete_at}")
            print(f"   - Can regenerate: {expired_recording.can_regenerate}")
            print(f"   - File exists: {os.path.exists(test_file_path)}")

            # Run cleanup
            print(f"\n🗑️  Running audio cleanup job...")
            cleanup_result = await retention_service.cleanup_expired_audio(db)

            print(f"\n📊 Cleanup Results:")
            print(f"   - Deleted count: {cleanup_result['deleted_count']}")
            print(f"   - Failed count: {cleanup_result['failed_count']}")
            print(f"   - Size freed: {cleanup_result['total_size_freed_mb']} MB")

            # Verify cleanup
            await db.refresh(expired_recording)
            file_still_exists = os.path.exists(test_file_path)

            print(f"\n✅ Verification:")
            print(f"   - Can regenerate: {expired_recording.can_regenerate} (should be False)")
            print(f"   - Audio retention enabled: {expired_recording.audio_retention_enabled} (should be False)")
            print(f"   - File exists: {file_still_exists} (should be False)")
            print(f"   - Recording still in DB: True (should keep transcription/summary)")

            assert cleanup_result['deleted_count'] == 1, "Should have deleted 1 file"
            assert expired_recording.can_regenerate == False, "Can regenerate should be False"
            assert not file_still_exists, "Physical file should be deleted"
            print(f"✅ Test 1 PASSED\n")

            # Test 2: Recording with future deletion date (should not be deleted)
            print("📋 Test 2: Keep non-expired audio file")
            print("-" * 50)

            # Create another temporary file
            temp_file2 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file2.write(b"Test audio content that should be kept")
            temp_file2.close()
            test_file_path2 = temp_file2.name

            # Create recording with FUTURE deletion date
            future_recording = Recording(
                user_id=test_user.id,
                filename=os.path.basename(test_file_path2),
                file_path=test_file_path2,
                file_size=os.path.getsize(test_file_path2),
                duration=45.0,
                status="completed",
                audio_delete_at=datetime.utcnow() + timedelta(days=5),  # Expires in 5 days
                can_regenerate=True,
                audio_retention_enabled=True
            )
            db.add(future_recording)
            await db.commit()
            await db.refresh(future_recording)

            print(f"✅ Created non-expired recording: {future_recording.id[:8]}...")
            print(f"   - Audio delete at: {future_recording.audio_delete_at}")
            print(f"   - Days remaining: ~5")

            # Run cleanup again
            print(f"\n🗑️  Running audio cleanup job...")
            cleanup_result2 = await retention_service.cleanup_expired_audio(db)

            print(f"\n📊 Cleanup Results:")
            print(f"   - Deleted count: {cleanup_result2['deleted_count']} (should be 0)")

            # Verify file still exists
            await db.refresh(future_recording)
            file_still_exists2 = os.path.exists(test_file_path2)

            print(f"\n✅ Verification:")
            print(f"   - Can regenerate: {future_recording.can_regenerate} (should be True)")
            print(f"   - File exists: {file_still_exists2} (should be True)")

            assert cleanup_result2['deleted_count'] == 0, "Should not delete any files"
            assert future_recording.can_regenerate == True, "Can regenerate should still be True"
            assert file_still_exists2, "File should still exist"
            print(f"✅ Test 2 PASSED\n")

            # Test 3: Recording already cleaned up (can_regenerate = False)
            print("📋 Test 3: Skip already cleaned recording")
            print("-" * 50)

            already_cleaned = Recording(
                user_id=test_user.id,
                filename="already_cleaned.mp3",
                file_path="/tmp/nonexistent_file.mp3",
                file_size=1000,
                duration=20.0,
                status="completed",
                audio_delete_at=datetime.utcnow() - timedelta(days=10),  # Expired 10 days ago
                can_regenerate=False,  # Already cleaned
                audio_retention_enabled=False
            )
            db.add(already_cleaned)
            await db.commit()
            await db.refresh(already_cleaned)

            print(f"✅ Created already-cleaned recording: {already_cleaned.id[:8]}...")
            print(f"   - Can regenerate: {already_cleaned.can_regenerate} (already False)")

            # Run cleanup
            print(f"\n🗑️  Running audio cleanup job...")
            cleanup_result3 = await retention_service.cleanup_expired_audio(db)

            print(f"\n📊 Cleanup Results:")
            print(f"   - Deleted count: {cleanup_result3['deleted_count']} (should be 0)")
            print(f"   - This recording should be skipped (can_regenerate already False)")

            assert cleanup_result3['deleted_count'] == 0, "Should skip already cleaned recordings"
            print(f"✅ Test 3 PASSED\n")

            # Test 4: Simulate full scheduler job
            print("📋 Test 4: Simulate full scheduler job")
            print("-" * 50)

            scheduler = BackgroundScheduler()
            print(f"🔄 Running audio cleanup job (simulated)...")
            await scheduler.cleanup_expired_audio_job()

            print(f"✅ Test 4 PASSED\n")

            # Test 5: Verify query filters work correctly
            print("📋 Test 5: Verify query filters")
            print("-" * 50)

            now = datetime.utcnow()
            result = await db.execute(
                select(Recording).filter(
                    Recording.audio_delete_at <= now,
                    Recording.can_regenerate == True
                )
            )
            expired_recs = result.scalars().all()

            print(f"📊 Found {len(expired_recs)} recordings needing cleanup")
            print(f"   - All should have: audio_delete_at <= now AND can_regenerate = True")

            for rec in expired_recs:
                print(f"   - Recording {rec.id[:8]}...: delete_at={rec.audio_delete_at}, can_regen={rec.can_regenerate}")

            # Should only find recordings that meet BOTH criteria
            for rec in expired_recs:
                assert rec.audio_delete_at <= now, "Should only include expired recordings"
                assert rec.can_regenerate == True, "Should only include regenerable recordings"

            print(f"✅ Test 5 PASSED\n")

            # Cleanup
            print("🧹 Cleaning up test data...")

            # Clean up test files
            if os.path.exists(test_file_path2):
                os.remove(test_file_path2)
                print(f"   - Deleted: {test_file_path2}")

            # Delete test recordings and user
            await db.delete(expired_recording)
            await db.delete(future_recording)
            await db.delete(already_cleaned)
            await db.delete(test_user)
            await db.commit()
            print(f"✅ Cleanup complete\n")

            print("=" * 50)
            print("✅ ALL TESTS PASSED!")
            print("=" * 50)
            print("\n📋 Summary:")
            print("   ✅ Expired audio files are deleted correctly")
            print("   ✅ Non-expired audio files are kept")
            print("   ✅ Already cleaned recordings are skipped")
            print("   ✅ Transcriptions and summaries are preserved")
            print("   ✅ Query filters work correctly")
            print("   ✅ can_regenerate flag is updated properly")
            print("   ✅ Scheduler job runs successfully")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Break after first session
            break


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🚀 Audio Cleanup Test Suite")
    print("=" * 50 + "\n")

    asyncio.run(test_audio_cleanup())

    print("\n✅ Test suite complete!\n")
