"""
Razorpay payment API endpoints for subscription management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date
from typing import Dict
import razorpay
import json
import hmac
import hashlib

from app.db.database import get_db
from app.models.user import User, SubscriptionTier
from app.core.config import settings
from app.core.dependencies import get_current_user

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

router = APIRouter(prefix="/payments", tags=["Payments"])

# Pricing configuration
# NOTE: You must create these plans in Razorpay Dashboard first and update the plan IDs
PRICING_PLANS = {
    "basic": {
        "name": "Basic",
        "monthly_price": 99900,  # ₹999 in paise
        "annual_price": 999900,  # ₹9999/year in paise (17% savings)
        "monthly_plan_id": "plan_S4ebA2udNY8X5M",
        "annual_plan_id": "plan_S4ebnOm5UdkjPT",
        "monthly_hours": 10,
        "features": [
            "10 hours of transcription per month",
            "AI-powered summaries",
            "4 summary formats",
            "Export to Word & PDF",
            "Save summaries to dashboard"
        ]
    },
    "pro": {
        "name": "Pro",
        "monthly_price": 199900,  # ₹1999 in paise
        "annual_price": 1999900,  # ₹19999/year in paise (17% savings)
        "monthly_plan_id": "plan_S4ecU7WUVvD2Tw",
        "annual_plan_id": "plan_S4ecvFLb3EhCFJ",
        "monthly_hours": 50,
        "features": [
            "50 hours of transcription per month",
            "Everything in Basic",
            "10-day audio retention",
            "Regenerate summaries",
            "Priority support"
        ]
    }
}


@router.get("/plans")
async def get_pricing_plans():
    """Get available subscription plans."""
    return {
        "plans": PRICING_PLANS,
        "key_id": settings.RAZORPAY_KEY_ID  # Public key for frontend
    }


@router.post("/create-checkout-session")
async def create_checkout_session(
    plan: str,
    interval: str = "month",  # "month" or "year"
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Razorpay subscription for checkout.
    Protected endpoint - requires authentication.
    Supports both monthly and annual billing.
    """
    # Validate plan input (prevent injection)
    plan = plan.lower().strip()
    if plan not in PRICING_PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan selected"
        )

    # Validate interval
    interval = interval.lower().strip()
    if interval not in ["month", "year"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid interval. Must be 'month' or 'year'"
        )

    # Verify Razorpay is configured
    if not settings.RAZORPAY_KEY_ID or len(settings.RAZORPAY_KEY_ID) < 10:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured"
        )

    # Check if user already has an active subscription
    if current_user.subscription_tier != SubscriptionTier.FREE:
        if current_user.subscription_expires_at and current_user.subscription_expires_at > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active subscription. Please cancel it first."
            )

    try:
        # Create or retrieve Razorpay customer
        if current_user.razorpay_customer_id:
            customer_id = current_user.razorpay_customer_id
        else:
            # Create new Razorpay customer
            customer_data = {
                "name": current_user.full_name or current_user.email,
                "email": current_user.email,
                "notes": {
                    "user_id": current_user.id,
                    "environment": "production" if not settings.DEBUG else "development"
                }
            }

            customer = razorpay_client.customer.create(data=customer_data)
            customer_id = customer["id"]
            current_user.razorpay_customer_id = customer_id
            await db.commit()

        # Select plan ID based on interval
        plan_config = PRICING_PLANS[plan]
        plan_id = plan_config["monthly_plan_id"] if interval == "month" else plan_config["annual_plan_id"]

        # Check if plan ID has been configured
        if "REPLACE_WITH" in plan_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment plans not configured. Please create plans in Razorpay Dashboard."
            )

        # Create subscription
        subscription_data = {
            "plan_id": plan_id,
            "customer_id": customer_id,
            "quantity": 1,
            "customer_notify": 1,  # Send notifications to customer
            "notes": {
                "user_id": current_user.id,
                "plan": plan,
                "interval": interval
            }
        }

        # For annual: 12 billing cycles, for monthly: large number for ongoing subscription
        if interval == "year":
            subscription_data["total_count"] = 12  # 12 months for annual
        else:
            subscription_data["total_count"] = 120  # 10 years worth of monthly billing

        subscription = razorpay_client.subscription.create(data=subscription_data)

        # Store subscription ID and plan ID
        current_user.razorpay_subscription_id = subscription["id"]
        current_user.razorpay_plan_id = plan_id
        await db.commit()

        return {
            "subscription_id": subscription["id"],
            "plan_id": plan_id,
            "key_id": settings.RAZORPAY_KEY_ID,
            "customer_id": customer_id
        }

    except razorpay.errors.BadRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating subscription: {str(e)}"
        )


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Razorpay webhook events.
    CRITICAL: Validates webhook signature to prevent fraudulent requests.
    """
    # Verify webhook secret is configured
    if not settings.RAZORPAY_WEBHOOK_SECRET or len(settings.RAZORPAY_WEBHOOK_SECRET) < 10:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret not configured"
        )

    payload = await request.body()
    webhook_signature = request.headers.get("X-Razorpay-Signature")

    # Validate signature header exists
    if not webhook_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header"
        )

    try:
        # CRITICAL: Verify webhook signature to prevent spoofing
        razorpay_client.utility.verify_webhook_signature(
            payload.decode('utf-8'),
            webhook_signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except Exception as e:
        # Invalid signature - potential attack
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    # Parse event
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    event_type = event.get("event")

    # Handle the event
    try:
        if event_type == "subscription.activated":
            subscription = event["payload"]["subscription"]["entity"]
            await handle_subscription_activated(subscription, db)

        elif event_type == "subscription.charged":
            subscription = event["payload"]["subscription"]["entity"]
            await handle_subscription_charged(subscription, db)

        elif event_type == "subscription.updated":
            subscription = event["payload"]["subscription"]["entity"]
            await handle_subscription_updated(subscription, db)

        elif event_type == "subscription.cancelled":
            subscription = event["payload"]["subscription"]["entity"]
            await handle_subscription_cancelled(subscription, db)

        elif event_type == "subscription.halted":
            subscription = event["payload"]["subscription"]["entity"]
            await handle_subscription_halted(subscription, db)

        # Acknowledge receipt of event
        return {"status": "success", "received": True}

    except Exception as e:
        # Log the error but return success to Razorpay to avoid retries
        # You should log this to your monitoring system
        print(f"Error processing webhook: {str(e)}")
        return {"status": "error", "message": "Internal processing error"}


async def handle_subscription_activated(subscription: Dict, db: AsyncSession):
    """
    Handle subscription activation (first payment success).
    Validates all data before updating user subscription.
    Sets monthly_hours_limit and subscription_anniversary_date.
    """
    from sqlalchemy import select

    customer_id = subscription.get("customer_id")

    if not customer_id:
        print(f"[WEBHOOK ERROR] Missing customer_id in subscription: {subscription.get('id')}")
        raise ValueError("Missing customer_id in subscription")

    result = await db.execute(
        select(User).filter(User.razorpay_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        print(f"[WEBHOOK ERROR] User not found for customer_id: {customer_id}")
        return

    print(f"[WEBHOOK] Activating subscription for user {user.email} (customer_id: {customer_id})")

    # Extract plan details from subscription
    plan_id = subscription.get("plan_id")
    notes = subscription.get("notes", {})
    plan = notes.get("plan", "").lower()
    interval = notes.get("interval", "month")

    # Validate plan
    if plan not in PRICING_PLANS:
        print(f"[WEBHOOK ERROR] Invalid plan: {plan}")
        raise ValueError(f"Invalid plan in subscription notes: {plan}")

    plan_config = PRICING_PLANS[plan]

    # Update user subscription
    if plan == "basic":
        user.subscription_tier = SubscriptionTier.BASIC
        user.monthly_hours_limit = 10.0
    elif plan == "pro":
        user.subscription_tier = SubscriptionTier.PRO
        user.monthly_hours_limit = 50.0

    # Set subscription details
    user.razorpay_subscription_id = subscription["id"]
    user.razorpay_plan_id = plan_id

    # Set subscription anniversary date (day of month for reset)
    today = date.today()
    user.subscription_anniversary_date = today

    # Razorpay provides current_start and current_end timestamps
    current_end = subscription.get("current_end")
    if current_end:
        user.subscription_expires_at = datetime.fromtimestamp(current_end)
        user.usage_reset_at = datetime.fromtimestamp(current_end)

    # Reset usage for new subscription
    user.monthly_hours_used = 0.0

    await db.commit()
    await db.refresh(user)

    print(f"[WEBHOOK SUCCESS] Subscription activated: user={user.email}, tier={user.subscription_tier.value}, hours={user.monthly_hours_limit}")


async def handle_subscription_charged(subscription: Dict, db: AsyncSession):
    """Handle successful recurring payment."""
    from sqlalchemy import select

    customer_id = subscription.get("customer_id")

    if not customer_id:
        return

    result = await db.execute(
        select(User).filter(User.razorpay_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update expiration date
        current_end = subscription.get("current_end")
        if current_end:
            user.subscription_expires_at = datetime.fromtimestamp(current_end)
            user.usage_reset_at = datetime.fromtimestamp(current_end)

        await db.commit()


async def handle_subscription_updated(subscription: Dict, db: AsyncSession):
    """Handle subscription updates (plan changes, etc.)."""
    from sqlalchemy import select

    customer_id = subscription.get("customer_id")

    if not customer_id:
        return

    result = await db.execute(
        select(User).filter(User.razorpay_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update expiration date if changed
        current_end = subscription.get("current_end")
        if current_end:
            user.subscription_expires_at = datetime.fromtimestamp(current_end)

        await db.commit()


async def handle_subscription_cancelled(subscription: Dict, db: AsyncSession):
    """Handle subscription cancellation."""
    from sqlalchemy import select

    customer_id = subscription.get("customer_id")

    if not customer_id:
        return

    result = await db.execute(
        select(User).filter(User.razorpay_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Downgrade to free tier
        user.subscription_tier = SubscriptionTier.FREE
        user.razorpay_subscription_id = None
        user.razorpay_plan_id = None
        user.subscription_expires_at = None
        user.monthly_hours_limit = None
        user.monthly_hours_used = 0.0

        await db.commit()


async def handle_subscription_halted(subscription: Dict, db: AsyncSession):
    """Handle subscription halted due to payment failure."""
    from sqlalchemy import select

    customer_id = subscription.get("customer_id")

    if not customer_id:
        return

    result = await db.execute(
        select(User).filter(User.razorpay_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Mark subscription as expired but don't delete - user might retry payment
        # Razorpay will send cancelled event if subscription is truly cancelled
        user.subscription_expires_at = datetime.utcnow() - timedelta(days=1)  # Mark as expired

        await db.commit()


@router.post("/change-plan")
async def change_plan(
    new_plan: str,
    new_interval: str = "month",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upgrade or downgrade subscription plan.
    Handles Basic ↔ Pro transitions.
    Note: Razorpay doesn't have built-in proration, so this cancels old subscription and creates new one.
    """
    if not current_user.razorpay_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found. Please subscribe first."
        )

    # Validate new plan
    new_plan = new_plan.lower().strip()
    if new_plan not in PRICING_PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan selected"
        )

    # Validate interval
    new_interval = new_interval.lower().strip()
    if new_interval not in ["month", "year"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid interval. Must be 'month' or 'year'"
        )

    # Check if already on this plan
    current_plan = current_user.subscription_tier.value
    if current_plan == new_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already on this plan"
        )

    try:
        # Cancel existing subscription
        razorpay_client.subscription.cancel(current_user.razorpay_subscription_id)

        # Create new subscription with new plan
        plan_config = PRICING_PLANS[new_plan]
        new_plan_id = plan_config["monthly_plan_id"] if new_interval == "month" else plan_config["annual_plan_id"]

        # Check if plan ID has been configured
        if "REPLACE_WITH" in new_plan_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment plans not configured"
            )

        subscription_data = {
            "plan_id": new_plan_id,
            "customer_id": current_user.razorpay_customer_id,
            "quantity": 1,
            "customer_notify": 1,
            "notes": {
                "user_id": current_user.id,
                "plan": new_plan,
                "interval": new_interval
            }
        }

        # For annual: 12 billing cycles, for monthly: large number for ongoing subscription
        if new_interval == "year":
            subscription_data["total_count"] = 12
        else:
            subscription_data["total_count"] = 120  # 10 years worth of monthly billing

        subscription = razorpay_client.subscription.create(data=subscription_data)

        # Update database
        if new_plan == "basic":
            current_user.subscription_tier = SubscriptionTier.BASIC
            current_user.monthly_hours_limit = 10.0
        elif new_plan == "pro":
            current_user.subscription_tier = SubscriptionTier.PRO
            current_user.monthly_hours_limit = 50.0

        current_user.razorpay_subscription_id = subscription["id"]
        current_user.razorpay_plan_id = new_plan_id

        # Update expiration
        current_end = subscription.get("current_end")
        if current_end:
            current_user.subscription_expires_at = datetime.fromtimestamp(current_end)

        await db.commit()

        return {
            "message": f"Plan changed to {plan_config['name']} successfully",
            "new_plan": new_plan,
            "monthly_hours_limit": current_user.monthly_hours_limit,
            "subscription_id": subscription["id"]
        }

    except razorpay.errors.BadRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing plan: {str(e)}"
        )


@router.post("/verify-subscription")
async def verify_and_activate_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually verify subscription status with Razorpay and activate if payment successful.
    This is a fallback for when webhooks are delayed or fail.
    """
    if not current_user.razorpay_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No subscription ID found. Please create a subscription first."
        )

    try:
        # Fetch subscription details from Razorpay
        subscription = razorpay_client.subscription.fetch(current_user.razorpay_subscription_id)

        print(f"[MANUAL VERIFY] Fetched subscription for {current_user.email}: status={subscription.get('status')}")

        # Check if subscription is active and paid
        if subscription.get("status") == "active":
            # Extract plan details
            notes = subscription.get("notes", {})
            plan = notes.get("plan", "").lower()
            plan_id = subscription.get("plan_id")

            # Only activate if not already activated
            if current_user.subscription_tier == SubscriptionTier.FREE or not current_user.monthly_hours_limit:
                print(f"[MANUAL VERIFY] Activating subscription for {current_user.email}")

                # Validate plan
                if plan not in PRICING_PLANS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid plan configuration: {plan}"
                    )

                # Update user subscription
                if plan == "basic":
                    current_user.subscription_tier = SubscriptionTier.BASIC
                    current_user.monthly_hours_limit = 10.0
                elif plan == "pro":
                    current_user.subscription_tier = SubscriptionTier.PRO
                    current_user.monthly_hours_limit = 50.0

                # Set subscription details
                current_user.razorpay_plan_id = plan_id

                # Set subscription anniversary date
                today = date.today()
                current_user.subscription_anniversary_date = today

                # Set expiration
                current_end = subscription.get("current_end")
                if current_end:
                    current_user.subscription_expires_at = datetime.fromtimestamp(current_end)
                    current_user.usage_reset_at = datetime.fromtimestamp(current_end)

                # Reset usage for new subscription
                current_user.monthly_hours_used = 0.0

                await db.commit()
                await db.refresh(current_user)

                print(f"[MANUAL VERIFY SUCCESS] Subscription activated: user={current_user.email}, tier={current_user.subscription_tier.value}")

                return {
                    "success": True,
                    "message": "Subscription activated successfully",
                    "subscription_tier": current_user.subscription_tier.value,
                    "monthly_hours_limit": current_user.monthly_hours_limit
                }
            else:
                # Already activated
                return {
                    "success": True,
                    "message": "Subscription already active",
                    "subscription_tier": current_user.subscription_tier.value,
                    "monthly_hours_limit": current_user.monthly_hours_limit
                }
        else:
            # Subscription not active yet
            return {
                "success": False,
                "message": f"Subscription status: {subscription.get('status')}. Payment may still be processing.",
                "status": subscription.get("status")
            }

    except razorpay.errors.BadRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"[MANUAL VERIFY ERROR] {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying subscription: {str(e)}"
        )


@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel user's subscription at end of billing cycle."""
    if not current_user.razorpay_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found"
        )

    try:
        # Cancel subscription at end of cycle
        razorpay_client.subscription.cancel(
            current_user.razorpay_subscription_id,
            data={"cancel_at_cycle_end": 1}
        )

        # Note: Subscription remains active until expiry
        # Webhook will handle final cleanup when subscription.cancelled event fires

        await db.commit()

        return {
            "message": "Subscription will be canceled at end of billing cycle",
            "expires_at": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None
        }

    except razorpay.errors.BadRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error canceling subscription: {str(e)}"
        )
