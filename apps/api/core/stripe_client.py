"""Stripe integration for billing."""

import logging
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.config import settings
from packages.db.models import User, Plan, Subscription

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_checkout_session(
    user: User,
    plan_name: str,
    session: AsyncSession,
) -> dict:
    """
    Create Stripe checkout session.

    Args:
        user: User object
        plan_name: Plan name (free, pro, enterprise)
        session: Database session

    Returns:
        Checkout session dict
    """
    # Get plan
    result = await session.execute(
        select(Plan).where(Plan.name == plan_name)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise ValueError(f"Plan not found: {plan_name}")

    # Create or get Stripe customer
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        user.stripe_customer_id = customer.id
        await session.commit()
    else:
        customer = stripe.Customer.retrieve(user.stripe_customer_id)

    # Create checkout session
    checkout_session = stripe.checkout.Session.create(
        customer=customer.id,
        payment_method_types=["card"],
        line_items=[
            {
                "price": plan.stripe_price_id,
                "quantity": 1,
            }
        ],
        mode="subscription",
        success_url=f"{settings.API_BASE_URL}/dashboard?success=true",
        cancel_url=f"{settings.API_BASE_URL}/pricing?canceled=true",
        metadata={
            "user_id": str(user.id),
            "plan_id": str(plan.id),
        },
    )

    logger.info(f"Created checkout session for user {user.id}: {checkout_session.id}")

    return {
        "checkout_url": checkout_session.url,
        "session_id": checkout_session.id,
    }


async def handle_subscription_created(
    event_data: dict,
    session: AsyncSession,
) -> None:
    """
    Handle subscription.created webhook.

    Args:
        event_data: Stripe event data
        session: Database session
    """
    subscription_obj = event_data["object"]
    customer_id = subscription_obj["customer"]

    # Get user
    result = await session.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.error(f"User not found for customer {customer_id}")
        return

    # Get plan from metadata
    metadata = subscription_obj.get("metadata", {})
    plan_id = metadata.get("plan_id")

    if not plan_id:
        logger.error("No plan_id in subscription metadata")
        return

    # Create subscription record
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan_id,
        stripe_subscription_id=subscription_obj["id"],
        status="active",
        current_period_start=subscription_obj["current_period_start"],
        current_period_end=subscription_obj["current_period_end"],
    )

    session.add(subscription)
    await session.commit()

    logger.info(f"Created subscription for user {user.id}")


async def handle_subscription_updated(
    event_data: dict,
    session: AsyncSession,
) -> None:
    """
    Handle subscription.updated webhook.

    Args:
        event_data: Stripe event data
        session: Database session
    """
    subscription_obj = event_data["object"]

    # Get subscription
    result = await session.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_obj["id"]
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        logger.error(f"Subscription not found: {subscription_obj['id']}")
        return

    # Update subscription
    subscription.status = subscription_obj["status"]
    subscription.current_period_start = subscription_obj["current_period_start"]
    subscription.current_period_end = subscription_obj["current_period_end"]

    await session.commit()

    logger.info(f"Updated subscription {subscription.id}")


async def handle_subscription_deleted(
    event_data: dict,
    session: AsyncSession,
) -> None:
    """
    Handle subscription.deleted webhook.

    Args:
        event_data: Stripe event data
        session: Database session
    """
    subscription_obj = event_data["object"]

    # Get subscription
    result = await session.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_obj["id"]
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        logger.error(f"Subscription not found: {subscription_obj['id']}")
        return

    # Mark as canceled
    subscription.status = "canceled"
    subscription.canceled_at = subscription_obj.get("canceled_at")

    await session.commit()

    logger.info(f"Canceled subscription {subscription.id}")


async def create_customer_portal_session(
    user: User,
) -> dict:
    """
    Create Stripe customer portal session.

    Args:
        user: User object

    Returns:
        Portal session dict
    """
    if not user.stripe_customer_id:
        raise ValueError("User has no Stripe customer ID")

    portal_session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.API_BASE_URL}/dashboard",
    )

    return {
        "portal_url": portal_session.url,
    }


def verify_webhook_signature(
    payload: bytes,
    signature: str,
) -> Optional[dict]:
    """
    Verify Stripe webhook signature.

    Args:
        payload: Request body
        signature: Stripe-Signature header

    Returns:
        Event dict or None if invalid
    """
    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
        return event
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return None
