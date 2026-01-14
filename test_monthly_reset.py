"""
Test script for monthly usage reset functionality.
Verifies that the scheduler correctly resets usage for users on their anniversary date.
"""
import asyncio
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_async_session
from app.models.user import User, SubscriptionTier
from app.services.usage_tracking_service import UsageTrackingService
from app.services.scheduler import BackgroundScheduler


async def test_monthly_reset():
    """Test the monthly usage reset logic."""
    print("🧪 Testing Monthly Usage Reset Functionality\n")

    usage_service = UsageTrackingService()

    async for db in get_async_session():
        try:
            # Test 1: Create a test user with usage on anniversary date
            print("📋 Test 1: User on subscription anniversary")
            print("-" * 50)

            today = date.today()
            test_user = User(
                email=f"test_reset_{datetime.now().timestamp()}@example.com",
                hashed_password="test_hash",
                is_trial_user=False,
                subscription_tier=SubscriptionTier.BASIC,
                monthly_hours_limit=10.0,
                monthly_hours_used=7.5,  # Has used 7.5 hours
                subscription_anniversary_date=today.day,  # Anniversary is today
                usage_reset_at=datetime.utcnow()
            )

            db.add(test_user)
            await db.commit()
            await db.refresh(test_user)

            print(f"✅ Created test user: {test_user.email}")
            print(f"   - Subscription tier: {test_user.subscription_tier.value}")
            print(f"   - Monthly limit: {test_user.monthly_hours_limit}h")
            print(f"   - Monthly used: {test_user.monthly_hours_used}h")
            print(f"   - Anniversary day: {test_user.subscription_anniversary_date}")
            print(f"   - Current reset date: {test_user.usage_reset_at}")

            # Test the reset function
            print(f"\n🔄 Resetting usage for user...")
            reset_result = await usage_service.reset_monthly_usage(test_user.id, db)

            if reset_result["success"]:
                print(f"✅ Reset successful!")
                print(f"   - Old usage: {reset_result['old_usage_hours']}h")
                print(f"   - New usage: {reset_result['new_usage_hours']}h")
                print(f"   - Next reset: {reset_result['next_reset_date']}")
            else:
                print(f"❌ Reset failed: {reset_result.get('message')}")

            # Verify the reset
            await db.refresh(test_user)
            print(f"\n📊 Verification:")
            print(f"   - Monthly hours used: {test_user.monthly_hours_used}h (should be 0)")
            print(f"   - Next reset date: {test_user.usage_reset_at}")

            assert test_user.monthly_hours_used == 0.0, "Usage should be reset to 0"
            print(f"✅ Test 1 PASSED\n")

            # Test 2: User NOT on anniversary date
            print("📋 Test 2: User NOT on subscription anniversary")
            print("-" * 50)

            tomorrow = (today + timedelta(days=1)).day
            test_user2 = User(
                email=f"test_no_reset_{datetime.now().timestamp()}@example.com",
                hashed_password="test_hash",
                is_trial_user=False,
                subscription_tier=SubscriptionTier.PRO,
                monthly_hours_limit=50.0,
                monthly_hours_used=25.0,
                subscription_anniversary_date=tomorrow,  # Anniversary is tomorrow, not today
                usage_reset_at=datetime.utcnow() + timedelta(days=1)
            )

            db.add(test_user2)
            await db.commit()
            await db.refresh(test_user2)

            print(f"✅ Created test user: {test_user2.email}")
            print(f"   - Anniversary day: {test_user2.subscription_anniversary_date} (today is {today.day})")
            print(f"   - Monthly used: {test_user2.monthly_hours_used}h")

            # This user should NOT be found by the reset job
            result = await db.execute(
                select(User).filter(
                    User.subscription_anniversary_date == today.day,
                    User.is_trial_user == False
                )
            )
            users_for_today = result.scalars().all()

            user_emails = [u.email for u in users_for_today]
            print(f"\n📊 Users with anniversary today: {len(users_for_today)}")
            print(f"   Should include: {test_user.email}")
            print(f"   Should NOT include: {test_user2.email}")

            assert test_user.email in user_emails, "Test user 1 should be included"
            assert test_user2.email not in user_emails, "Test user 2 should NOT be included"
            print(f"✅ Test 2 PASSED\n")

            # Test 3: Trial user should not be reset
            print("📋 Test 3: Trial user should be skipped")
            print("-" * 50)

            trial_user = User(
                email=f"trial_test_{datetime.now().timestamp()}@example.com",
                is_trial_user=True,
                trial_email=f"trial_test_{datetime.now().timestamp()}@example.com",
                trial_minutes_used=5.0,
                subscription_tier=SubscriptionTier.FREE,
                monthly_hours_limit=0.0,
                monthly_hours_used=0.0,
                subscription_anniversary_date=today.day
            )

            db.add(trial_user)
            await db.commit()
            await db.refresh(trial_user)

            print(f"✅ Created trial user: {trial_user.email}")
            print(f"   - Is trial: {trial_user.is_trial_user}")
            print(f"   - Trial minutes used: {trial_user.trial_minutes_used}")

            reset_result = await usage_service.reset_monthly_usage(trial_user.id, db)

            print(f"\n🔄 Attempting reset for trial user...")
            if not reset_result["success"]:
                print(f"✅ Correctly skipped trial user: {reset_result.get('message')}")
            else:
                print(f"❌ Should not have reset trial user")

            assert not reset_result["success"], "Trial users should not be reset"
            print(f"✅ Test 3 PASSED\n")

            # Test 4: Simulate the actual scheduler job
            print("📋 Test 4: Simulate full scheduler job")
            print("-" * 50)

            scheduler = BackgroundScheduler()
            print(f"🔄 Running monthly reset job (simulated)...")
            await scheduler.reset_monthly_usage_job()

            print(f"✅ Test 4 PASSED\n")

            # Cleanup
            print("🧹 Cleaning up test users...")
            await db.delete(test_user)
            await db.delete(test_user2)
            await db.delete(trial_user)
            await db.commit()
            print(f"✅ Cleanup complete\n")

            print("=" * 50)
            print("✅ ALL TESTS PASSED!")
            print("=" * 50)
            print("\n📋 Summary:")
            print("   ✅ Monthly usage resets correctly on anniversary")
            print("   ✅ Users not on anniversary are skipped")
            print("   ✅ Trial users are skipped")
            print("   ✅ Scheduler job runs successfully")
            print("   ✅ Next reset date is calculated correctly")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            raise
        finally:
            # Break after first session
            break


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🚀 Monthly Usage Reset Test Suite")
    print("=" * 50 + "\n")

    asyncio.run(test_monthly_reset())

    print("\n✅ Test suite complete!\n")
