"""
Stripe payment API endpoints for subscription management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date
from typing import Dict
import stripe

from app.db.database import get_db
from app.models.user import User, SubscriptionTier
from app.core.config import settings
from app.core.dependencies import get_current_user

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/payments", tags=["Payments"])

# Pricing configuration
PRICING_PLANS = {
    "basic": {
        "name": "Basic",
        "monthly_price": 999,  # $9.99 in cents
        "annual_price": 9900,  # $99/year in cents (17% savings)
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
        "monthly_price": 1999,  # $19.99 in cents
        "annual_price": 19900,  # $199/year in cents (17% savings)
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
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY
    }


@router.post("/create-checkout-session")
async def create_checkout_session(
    plan: str,
    interval: str = "month",  # "month" or "year"
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe checkout session for subscription.
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

    # Verify Stripe is configured
    if not settings.STRIPE_SECRET_KEY or len(settings.STRIPE_SECRET_KEY) < 10:
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
        # Create or retrieve Stripe customer
        if current_user.stripe_customer_id:
            # Verify customer exists in Stripe
            try:
                stripe.Customer.retrieve(current_user.stripe_customer_id)
                customer_id = current_user.stripe_customer_id
            except stripe.error.InvalidRequestError:
                # Customer doesn't exist, create new one
                customer = stripe.Customer.create(
                    email=current_user.email,
                    metadata={
                        "user_id": current_user.id,
                        "environment": "production" if not settings.DEBUG else "development"
                    }
                )
                customer_id = customer.id
                current_user.stripe_customer_id = customer_id
                await db.commit()
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={
                    "user_id": current_user.id,
                    "environment": "production" if not settings.DEBUG else "development"
                }
            )
            customer_id = customer.id
            current_user.stripe_customer_id = customer_id
            await db.commit()

        # Create checkout session
        plan_config = PRICING_PLANS[plan]

        # Select price based on interval
        unit_amount = plan_config["monthly_price"] if interval == "month" else plan_config["annual_price"]

        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"{plan_config['name']} Plan - {'Monthly' if interval == 'month' else 'Annual'}",
                        "description": ", ".join(plan_config["features"][:3]),
                    },
                    "unit_amount": unit_amount,
                    "recurring": {
                        "interval": interval
                    }
                },
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{settings.CORS_ORIGINS[0]}/subscribe?session_id={{CHECKOUT_SESSION_ID}}&success=true",
            cancel_url=f"{settings.CORS_ORIGINS[0]}/subscribe?canceled=true",
            metadata={
                "user_id": current_user.id,
                "plan": plan,
                "interval": interval
            }
        )

        return {"session_id": checkout_session.id, "url": checkout_session.url}

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events.
    CRITICAL: Validates webhook signature to prevent fraudulent requests.
    """
    # Verify webhook secret is configured
    if not settings.STRIPE_WEBHOOK_SECRET or len(settings.STRIPE_WEBHOOK_SECRET) < 10:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret not configured"
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Validate signature header exists
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header"
        )

    try:
        # CRITICAL: Verify webhook signature to prevent spoofing
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature - potential attack
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    # Handle the event
    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            await handle_checkout_session_completed(session, db)

        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            await handle_subscription_updated(subscription, db)

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await handle_subscription_deleted(subscription, db)

        # Acknowledge receipt of event
        return {"status": "success", "received": True}

    except Exception as e:
        # Log the error but return success to Stripe to avoid retries
        # You should log this to your monitoring system
        print(f"Error processing webhook: {str(e)}")
        return {"status": "error", "message": "Internal processing error"}


async def handle_checkout_session_completed(session: Dict, db: AsyncSession):
    """
    Handle successful checkout session.
    Validates all data before updating user subscription.
    Sets monthly_hours_limit and subscription_anniversary_date.
    """
    from sqlalchemy import select

    # Validate required fields exist
    if "metadata" not in session or "user_id" not in session["metadata"]:
        raise ValueError("Missing user_id in session metadata")

    user_id = session["metadata"]["user_id"]
    plan = session["metadata"].get("plan", "").lower()
    interval = session["metadata"].get("interval", "month")

    # Validate plan
    if plan not in PRICING_PLANS:
        raise ValueError(f"Invalid plan in metadata: {plan}")

    subscription_id = session.get("subscription")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if user:
        # Get plan configuration
        plan_config = PRICING_PLANS[plan]

        # Update user subscription
        if plan == "basic":
            user.subscription_tier = SubscriptionTier.BASIC
            user.monthly_hours_limit = 10.0
        elif plan == "pro":
            user.subscription_tier = SubscriptionTier.PRO
            user.monthly_hours_limit = 50.0

        # Set subscription details
        user.stripe_subscription_id = subscription_id

        # Set subscription anniversary date (day of month for reset)
        today = date.today()
        user.subscription_anniversary_date = today

        # Calculate next reset date
        if interval == "month":
            # Monthly subscription - expires in 30 days
            user.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
            user.usage_reset_at = datetime.utcnow() + timedelta(days=30)
        else:
            # Annual subscription - expires in 365 days
            user.subscription_expires_at = datetime.utcnow() + timedelta(days=365)
            user.usage_reset_at = datetime.utcnow() + timedelta(days=30)  # Still reset monthly

        # Reset usage for new subscription
        user.monthly_hours_used = 0.0

        await db.commit()


async def handle_subscription_updated(subscription: Dict, db: AsyncSession):
    """Handle subscription updates."""
    from sqlalchemy import select

    customer_id = subscription["customer"]
    result = await db.execute(select(User).filter(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()

    if user:
        # Update subscription expiration
        user.subscription_expires_at = datetime.fromtimestamp(subscription["current_period_end"])
        await db.commit()


async def handle_subscription_deleted(subscription: Dict, db: AsyncSession):
    """Handle subscription cancellation."""
    from sqlalchemy import select

    customer_id = subscription["customer"]
    result = await db.execute(select(User).filter(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()

    if user:
        # Downgrade to free tier
        user.subscription_tier = SubscriptionTier.FREE
        user.stripe_subscription_id = None
        user.subscription_expires_at = None
        await db.commit()


@router.post("/change-plan")
async def change_plan(
    new_plan: str,
    new_interval: str = "month",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upgrade or downgrade subscription plan with prorated billing.
    Handles Basic ↔ Pro transitions.
    """
    if not current_user.stripe_subscription_id:
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
        # Get current subscription from Stripe
        subscription = stripe.Subscription.retrieve(current_user.stripe_subscription_id)

        # Get new plan config
        plan_config = PRICING_PLANS[new_plan]
        new_price = plan_config["monthly_price"] if new_interval == "month" else plan_config["annual_price"]

        # Create new price in Stripe or use existing
        price = stripe.Price.create(
            unit_amount=new_price,
            currency="usd",
            recurring={"interval": new_interval},
            product_data={
                "name": f"{plan_config['name']} Plan - {'Monthly' if new_interval == 'month' else 'Annual'}",
            },
        )

        # Update subscription with proration
        updated_subscription = stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            items=[{
                "id": subscription["items"]["data"][0].id,
                "price": price.id,
            }],
            proration_behavior="create_prorations",  # Enable proration
            metadata={
                "user_id": current_user.id,
                "plan": new_plan,
                "interval": new_interval
            }
        )

        # Update user in database
        if new_plan == "basic":
            current_user.subscription_tier = SubscriptionTier.BASIC
            current_user.monthly_hours_limit = 10.0
        elif new_plan == "pro":
            current_user.subscription_tier = SubscriptionTier.PRO
            current_user.monthly_hours_limit = 50.0

        # Update expiration based on new interval
        current_user.subscription_expires_at = datetime.fromtimestamp(
            updated_subscription["current_period_end"]
        )

        await db.commit()

        return {
            "message": f"Plan changed to {plan_config['name']} successfully",
            "new_plan": new_plan,
            "monthly_hours_limit": current_user.monthly_hours_limit,
            "proration_applied": True
        }

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel user's subscription."""
    if not current_user.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found"
        )

    try:
        stripe.Subscription.delete(current_user.stripe_subscription_id)

        # Update user
        current_user.subscription_tier = SubscriptionTier.FREE
        current_user.stripe_subscription_id = None
        current_user.subscription_expires_at = None
        current_user.monthly_hours_limit = None
        current_user.monthly_hours_used = 0.0

        await db.commit()

        return {"message": "Subscription canceled successfully"}

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
